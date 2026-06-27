import re
from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from src.modules.inventory.models import InventoryItem, InventoryStatus
from src.modules.products.models import Product
from src.modules.recipes.models import (
    Recipe,
    RecipeIngredientAvailability,
    RecipeIngredientDetail,
    RecipeQuery,
    RecipeStepDetail,
)
from src.modules.recipes.schemas import (
    RecipeDetailResponseSchema,
    RecipeIngredientDetailResponseSchema,
    RecipeResponseSchema,
    RecipeSearchRequestSchema,
    RecipeStepDetailResponseSchema,
)
from src.modules.recipes.spoonacular_client import SpoonacularClient

MAX_INGREDIENTS = 15


class RecipeService:
    def __init__(self) -> None:
        self.spoonacular_client = SpoonacularClient()

    def _normalize_name(self, name: str) -> str:
        value = name.strip().lower()
        value = re.sub(r'[^a-z0-9\s\-]', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        if value.endswith('s') and len(value) > 3:  # noqa: PLR2004
            value = value[:-1]

        return value

    def _is_match(
        self,
        inventory_name: str,
        recipe_ingredient_name: str,
    ) -> bool:
        inventory_normalized = self._normalize_name(inventory_name)
        recipe_normalized = self._normalize_name(recipe_ingredient_name)

        if not inventory_normalized or not recipe_normalized:
            return False

        return inventory_normalized in recipe_normalized or recipe_normalized in inventory_normalized

    def _compute_match_score(
        self,
        inventory_names: list[str],
        recipe_ingredient_names: list[str],
    ) -> float:
        if not recipe_ingredient_names:
            return 0.0

        matched_count = 0

        for recipe_ingredient_name in recipe_ingredient_names:
            if any(
                self._is_match(
                    inventory_name=inventory_name,
                    recipe_ingredient_name=recipe_ingredient_name,
                )
                for inventory_name in inventory_names
            ):
                matched_count += 1

        return round(
            (matched_count / len(recipe_ingredient_names)) * 100,
            1,
        )

    def _extract_ingredient_ids(self, recipe_data: dict) -> list[int]:
        ingredient_ids: set[int] = set()

        for key in ('usedIngredients', 'missedIngredients', 'unusedIngredients'):
            for ingredient in recipe_data.get(key, []):
                ingredient_id = ingredient.get('id')

                if ingredient_id is not None:
                    ingredient_ids.add(int(ingredient_id))

        return list(ingredient_ids)

    def _extract_ingredient_names(self, recipe_data: dict) -> list[str]:
        names: set[str] = set()

        for key in ('usedIngredients', 'missedIngredients'):
            for ingredient in recipe_data.get(key, []):
                name = (ingredient.get('name') or '').strip().lower()

                if name:
                    names.add(name)

        return list(names)

    def _extract_used_ingredient_count(self, recipe_data: dict) -> int:
        return len(recipe_data.get('usedIngredients', []))

    def _extract_missed_ingredient_count(self, recipe_data: dict) -> int:
        return len(recipe_data.get('missedIngredients', []))

    async def _get_inventory_item_name(
        self,
        item: InventoryItem,
    ) -> str | None:
        if item.custom_name:
            return item.custom_name

        if item.product_id:
            product = await Product.get(item.product_id)

            if product:
                return product.name

        if item.barcode:
            return item.barcode

        return None

    async def _get_inventory_context(
        self,
        user_id: str,
    ) -> tuple[list[InventoryItem], list[str]]:
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid user id',
            )

        items = (
            await InventoryItem.find(
                InventoryItem.user_id == user_object_id,
                InventoryItem.status == InventoryStatus.ACTIVE,
            )
            .sort(InventoryItem.expiration_date)
            .to_list()
        )

        seen: set[str] = set()
        names: list[str] = []

        for item in items:
            name = await self._get_inventory_item_name(item)

            if not name:
                continue

            normalized_name = self._normalize_name(name)

            if not normalized_name or normalized_name in seen:
                continue

            seen.add(normalized_name)
            names.append(name)

        return items, names[:MAX_INGREDIENTS]

    async def _save_recipe_from_spoonacular(
        self,
        recipe_data: dict,
    ) -> Recipe:
        spoonacular_id = int(recipe_data['id'])

        existing_recipe = await Recipe.find_one(
            Recipe.spoonacular_id == spoonacular_id,
        )

        if existing_recipe:
            return existing_recipe

        recipe = Recipe(
            spoonacular_id=spoonacular_id,
            title=recipe_data['title'],
            image=recipe_data.get('image'),
            ingredient_ids=self._extract_ingredient_ids(recipe_data),
            ingredient_names=self._extract_ingredient_names(recipe_data),
            details_fetched=False,
        )

        try:
            await recipe.insert()
        except DuplicateKeyError:
            existing_recipe = await Recipe.find_one(
                Recipe.spoonacular_id == spoonacular_id,
            )

            if existing_recipe:
                return existing_recipe

            raise

        return recipe

    async def _cache_query(
        self,
        ingredient_names: list[str],
        recipe_ids: list[int],
    ) -> None:
        normalized_ingredients = [
            self._normalize_name(ingredient_name)
            for ingredient_name in ingredient_names
            if self._normalize_name(ingredient_name)
        ]

        query_key = ','.join(sorted(normalized_ingredients))

        existing_query = await RecipeQuery.find_one(
            RecipeQuery.query == query_key,
        )

        if existing_query:
            existing_query.ingredients = normalized_ingredients
            existing_query.recipe_ids = recipe_ids
            existing_query.updated_at = datetime.now(UTC)
            await existing_query.save()
            return

        query = RecipeQuery(
            query=query_key,
            ingredients=normalized_ingredients,
            recipe_ids=recipe_ids,
        )

        try:
            await query.insert()
        except DuplicateKeyError:
            existing_query = await RecipeQuery.find_one(
                RecipeQuery.query == query_key,
            )

            if existing_query:
                existing_query.ingredients = normalized_ingredients
                existing_query.recipe_ids = recipe_ids
                existing_query.updated_at = datetime.now(UTC)
                await existing_query.save()

    async def get_recipes_by_inventory(
        self,
        data: RecipeSearchRequestSchema,
        user_id: str,
    ) -> list[RecipeResponseSchema]:
        _, inventory_names = await self._get_inventory_context(user_id)

        if not inventory_names:
            return []

        normalized_inventory_names = [
            self._normalize_name(name) for name in inventory_names if self._normalize_name(name)
        ]

        query_key = ','.join(sorted(normalized_inventory_names))

        cached_query = await RecipeQuery.find_one(
            RecipeQuery.query == query_key,
        )

        recipes: list[Recipe] = []

        if cached_query and cached_query.recipe_ids:
            recipes = await Recipe.find(
                Recipe.spoonacular_id in cached_query.recipe_ids,
            ).to_list()

        if len(recipes) < data.number:
            spoonacular_results = await self.spoonacular_client.find_recipes_by_ingredients(
                ingredients=normalized_inventory_names,
                number=data.number,
            )

            recipes = []

            for recipe_data in spoonacular_results:
                recipe = await self._save_recipe_from_spoonacular(recipe_data)
                recipes.append(recipe)

            await self._cache_query(
                ingredient_names=inventory_names,
                recipe_ids=[recipe.spoonacular_id for recipe in recipes],
            )

        response_items: list[RecipeResponseSchema] = []

        for recipe in recipes:
            match_score = self._compute_match_score(
                inventory_names=inventory_names,
                recipe_ingredient_names=recipe.ingredient_names,
            )

            used_ingredient_count = 0
            missed_ingredient_count = 0

            if recipe.ingredient_names:
                for recipe_ingredient_name in recipe.ingredient_names:
                    has_match = any(
                        self._is_match(
                            inventory_name=inventory_name,
                            recipe_ingredient_name=recipe_ingredient_name,
                        )
                        for inventory_name in inventory_names
                    )

                    if has_match:
                        used_ingredient_count += 1
                    else:
                        missed_ingredient_count += 1

            response_items.append(
                RecipeResponseSchema(
                    spoonacular_id=recipe.spoonacular_id,
                    title=recipe.title,
                    image=recipe.image,
                    match_score=match_score,
                    used_ingredient_count=used_ingredient_count,
                    missed_ingredient_count=missed_ingredient_count,
                )
            )

        response_items.sort(
            key=lambda recipe: recipe.match_score,
            reverse=True,
        )

        return response_items[: data.number]

    def _parse_recipe_details(
        self,
        data: dict,
    ) -> tuple[
        int | None,
        int | None,
        float | None,
        list[RecipeIngredientDetail],
        list[RecipeStepDetail],
    ]:
        calories = None

        for nutrient in data.get('nutrition', {}).get('nutrients', []):
            if nutrient.get('name') == 'Calories':
                calories = nutrient.get('amount')
                break

        ingredients = [
            RecipeIngredientDetail(
                id=ingredient.get('id'),
                name=ingredient.get('nameClean') or ingredient.get('name', ''),
                amount=ingredient.get('amount', 0),
                unit=ingredient.get('unit', ''),
            )
            for ingredient in data.get('extendedIngredients', [])
        ]

        steps: list[RecipeStepDetail] = []
        analyzed_instructions = data.get('analyzedInstructions', [])

        if analyzed_instructions:
            for step in analyzed_instructions[0].get('steps', []):
                steps.append(
                    RecipeStepDetail(
                        number=step.get('number', 0),
                        step=step.get('step', ''),
                    )
                )

        return (
            data.get('readyInMinutes'),
            data.get('servings'),
            calories,
            ingredients,
            steps,
        )

    async def _get_or_fetch_recipe_details(
        self,
        spoonacular_id: int,
    ) -> Recipe:
        recipe = await Recipe.find_one(
            Recipe.spoonacular_id == spoonacular_id,
        )

        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Recipe not found. Search recipes first.',
            )

        if recipe.details_fetched:
            return recipe

        data = await self.spoonacular_client.get_recipe_information(
            recipe_id=spoonacular_id,
        )

        (
            recipe.ready_in_minutes,
            recipe.servings,
            recipe.calories,
            recipe.ingredients,
            recipe.steps,
        ) = self._parse_recipe_details(data)

        recipe.details_fetched = True
        recipe.updated_at = datetime.now(UTC)

        await recipe.save()

        return recipe

    def _find_matching_inventory_item(
        self,
        ingredient_name: str,
        inventory_items_with_names: list[tuple[InventoryItem, str]],
    ) -> tuple[InventoryItem, str] | None:
        for item, inventory_name in inventory_items_with_names:
            if self._is_match(
                inventory_name=inventory_name,
                recipe_ingredient_name=ingredient_name,
            ):
                return item, inventory_name

        return None

    async def get_recipe_details(
        self,
        spoonacular_id: int,
        user_id: str,
    ) -> RecipeDetailResponseSchema:
        recipe = await self._get_or_fetch_recipe_details(spoonacular_id)

        inventory_items, _ = await self._get_inventory_context(user_id)

        inventory_items_with_names: list[tuple[InventoryItem, str]] = []

        for item in inventory_items:
            name = await self._get_inventory_item_name(item)

            if name:
                inventory_items_with_names.append((item, name))

        ingredients: list[RecipeIngredientDetailResponseSchema] = []

        for ingredient in recipe.ingredients:
            matching_item = self._find_matching_inventory_item(
                ingredient_name=ingredient.name,
                inventory_items_with_names=inventory_items_with_names,
            )

            if matching_item:
                item, _ = matching_item

                availability_status = RecipeIngredientAvailability.AVAILABLE
                inventory_item_id = str(item.id)
                inventory_amount = item.amount
                inventory_unit = item.unit
            else:
                availability_status = RecipeIngredientAvailability.MISSING
                inventory_item_id = None
                inventory_amount = None
                inventory_unit = None

            ingredients.append(
                RecipeIngredientDetailResponseSchema(
                    id=ingredient.id,
                    name=ingredient.name,
                    amount=ingredient.amount,
                    unit=ingredient.unit,
                    availability_status=availability_status,
                    inventory_item_id=inventory_item_id,
                    inventory_amount=inventory_amount,
                    inventory_unit=inventory_unit,
                )
            )

        return RecipeDetailResponseSchema(
            spoonacular_id=recipe.spoonacular_id,
            title=recipe.title,
            image=recipe.image,
            ready_in_minutes=recipe.ready_in_minutes,
            servings=recipe.servings,
            calories=recipe.calories,
            ingredients=ingredients,
            steps=[
                RecipeStepDetailResponseSchema(
                    number=step.number,
                    step=step.step,
                )
                for step in recipe.steps
            ],
        )

# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Business logic for fetching and caching recipe recommendations.
# First Written on: Tuesday, 19-May-2026
# Edited on: Monday, 13-Jul-2026

import asyncio
import re
from datetime import UTC, datetime

from beanie import PydanticObjectId
from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError
from src.modules.ingredients.services import IngredientNormalizationService
from src.modules.inventory.models import InventoryItem, InventoryStatus, InventoryUnits
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
        self.normalization_service = IngredientNormalizationService()

    def _normalize_name(self, name: str) -> str:
        value = name.strip().lower()
        value = re.sub(r'[^a-z0-9\s\-]', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip()

        if value.endswith('s') and len(value) > 3:  # noqa: PLR2004
            value = value[:-1]

        return value

    def _normalize_unit(
        self,
        unit: str | InventoryUnits | None,
    ) -> str | None:
        if unit is None:
            return None

        value = unit.value if isinstance(unit, InventoryUnits) else unit
        value = value.strip().lower().replace('.', '')

        if not value:
            return None

        aliases = {
            'g': 'g',
            'gram': 'g',
            'grams': 'g',
            'kg': 'kg',
            'kilogram': 'kg',
            'kilograms': 'kg',
            'ml': 'ml',
            'milliliter': 'ml',
            'milliliters': 'ml',
            'millilitre': 'ml',
            'millilitres': 'ml',
            'l': 'l',
            'liter': 'l',
            'liters': 'l',
            'litre': 'l',
            'litres': 'l',
            'pc': 'pcs',
            'pcs': 'pcs',
            'piece': 'pcs',
            'pieces': 'pcs',
            'unit': 'pcs',
            'units': 'pcs',
        }

        return aliases.get(value)

    def _unit_group_and_base_multiplier(
        self,
        unit: str | None,
    ) -> tuple[str, float] | None:
        if unit is None:
            return None

        units = {
            'g': ('mass', 1.0),
            'kg': ('mass', 1000.0),
            'ml': ('volume', 1.0),
            'l': ('volume', 1000.0),
            'pcs': ('count', 1.0),
        }

        return units.get(unit)

    def _convert_to_base_amount(
        self,
        amount: float | None,
        unit: str | None,
    ) -> tuple[str, float] | None:
        if amount is None:
            return None

        unit_info = self._unit_group_and_base_multiplier(unit)

        if unit_info is None:
            return None

        unit_group, multiplier = unit_info

        return unit_group, amount * multiplier

    def _inventory_unit_from_normalized(
        self,
        unit: str,
    ) -> InventoryUnits | None:
        try:
            return InventoryUnits(unit)
        except ValueError:
            return None

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

    async def _get_product_map(
        self,
        items: list[InventoryItem],
    ) -> dict[PydanticObjectId, Product]:
        product_ids = [item.product_id for item in items if item.product_id]

        if not product_ids:
            return {}

        products = await Product.find({'_id': {'$in': product_ids}}).to_list()

        return {product.id: product for product in products}

    def _get_inventory_item_name_and_tags(
        self,
        item: InventoryItem,
        product_map: dict[PydanticObjectId, Product],
    ) -> tuple[str | None, list[str]]:
        if item.product_id:
            product = product_map.get(item.product_id)

            if product:
                return product.name, product.tags

        if item.custom_name:
            return item.custom_name, []

        if item.barcode:
            return item.barcode, []

        return None, []

    async def _normalize_inventory_items(
        self,
        items: list[InventoryItem],
    ) -> list[tuple[InventoryItem, str]]:
        product_map = await self._get_product_map(items)

        candidates: list[tuple[InventoryItem, str, list[str]]] = []

        for item in items:
            raw_name, tags = self._get_inventory_item_name_and_tags(item, product_map)

            if raw_name:
                candidates.append((item, raw_name, tags))

        normalized_results = await asyncio.gather(
            *(self.normalization_service.normalize(raw=raw_name, tags=tags) for _, raw_name, tags in candidates)
        )

        items_with_names: list[tuple[InventoryItem, str]] = []

        for (item, raw_name, _tags), normalized_name in zip(candidates, normalized_results, strict=True):
            final_name = normalized_name or self._normalize_name(raw_name)

            if final_name:
                items_with_names.append((item, final_name))

        return items_with_names

    async def _load_active_inventory_items(
        self,
        user_id: str,
    ) -> list[InventoryItem]:
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid user id',
            )

        return (
            await InventoryItem.find(
                InventoryItem.user_id == user_object_id,
                InventoryItem.status == InventoryStatus.ACTIVE,
            )
            .sort(InventoryItem.expiration_date)
            .to_list()
        )

    async def _get_inventory_context(
        self,
        user_id: str,
    ) -> tuple[list[InventoryItem], list[str]]:
        items = await self._load_active_inventory_items(user_id)
        items_with_names = await self._normalize_inventory_items(items)

        seen: set[str] = set()
        normalized_names: list[str] = []

        for _, normalized_name in items_with_names:
            if normalized_name in seen:
                continue

            seen.add(normalized_name)
            normalized_names.append(normalized_name)

        return items, normalized_names[:MAX_INGREDIENTS]

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
        spoonacular_score_map: dict[int, tuple[int, int, float]] = {}

        if cached_query and cached_query.recipe_ids:
            recipes = await Recipe.find(
                {
                    'spoonacular_id': {
                        '$in': cached_query.recipe_ids,
                    },
                }
            ).to_list()

        if len(recipes) < data.number:
            spoonacular_results = await self.spoonacular_client.find_recipes_by_ingredients(
                ingredients=normalized_inventory_names,
                number=data.number,
            )

            recipes = []
            spoonacular_score_map = {}

            for recipe_data in spoonacular_results:
                recipe = await self._save_recipe_from_spoonacular(recipe_data)
                recipes.append(recipe)

                used_count = self._extract_used_ingredient_count(recipe_data)
                missed_count = self._extract_missed_ingredient_count(recipe_data)
                total_count = used_count + missed_count

                match_score = (
                    round(
                        (used_count / total_count) * 100,
                        1,
                    )
                    if total_count
                    else 0.0
                )

                spoonacular_score_map[recipe.spoonacular_id] = (
                    used_count,
                    missed_count,
                    match_score,
                )

            await self._cache_query(
                ingredient_names=inventory_names,
                recipe_ids=[recipe.spoonacular_id for recipe in recipes],
            )

        response_items: list[RecipeResponseSchema] = []

        for recipe in recipes:
            spoonacular_score = spoonacular_score_map.get(recipe.spoonacular_id)

            if spoonacular_score:
                used_ingredient_count, missed_ingredient_count, match_score = spoonacular_score
            else:
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

    def _find_matching_inventory_items(
        self,
        ingredient_name: str,
        inventory_items_with_names: list[tuple[InventoryItem, str]],
    ) -> list[tuple[InventoryItem, str]]:
        matching_items: list[tuple[InventoryItem, str]] = []

        for item, inventory_name in inventory_items_with_names:
            if self._is_match(
                inventory_name=inventory_name,
                recipe_ingredient_name=ingredient_name,
            ):
                matching_items.append((item, inventory_name))

        return matching_items

    def _build_ingredient_availability(
        self,
        ingredient: RecipeIngredientDetail,
        matching_items: list[tuple[InventoryItem, str]],
    ) -> tuple[
        RecipeIngredientAvailability,
        str | None,
        float | None,
        InventoryUnits | None,
        bool,
    ]:
        if not matching_items:
            return (
                RecipeIngredientAvailability.MISSING,
                None,
                None,
                None,
                False,
            )

        recipe_unit = self._normalize_unit(ingredient.unit)
        recipe_base_amount = self._convert_to_base_amount(
            amount=ingredient.amount,
            unit=recipe_unit,
        )

        first_item = matching_items[0][0]

        if recipe_base_amount is None:
            return (
                RecipeIngredientAvailability.UNKNOWN_AMOUNT,
                str(first_item.id),
                first_item.amount,
                first_item.unit,
                False,
            )

        recipe_unit_group, required_base_amount = recipe_base_amount

        total_inventory_base_amount = 0.0
        comparable_items: list[InventoryItem] = []

        for item, _ in matching_items:
            inventory_unit = self._normalize_unit(item.unit)
            inventory_base_amount = self._convert_to_base_amount(
                amount=item.amount,
                unit=inventory_unit,
            )

            if inventory_base_amount is None:
                continue

            inventory_unit_group, item_base_amount = inventory_base_amount

            if inventory_unit_group != recipe_unit_group:
                continue

            total_inventory_base_amount += item_base_amount
            comparable_items.append(item)

        if not comparable_items:
            return (
                RecipeIngredientAvailability.UNKNOWN_AMOUNT,
                str(first_item.id),
                first_item.amount,
                first_item.unit,
                False,
            )

        representative_item = comparable_items[0]

        if total_inventory_base_amount >= required_base_amount:
            availability_status = RecipeIngredientAvailability.AVAILABLE
        else:
            availability_status = RecipeIngredientAvailability.INSUFFICIENT

        return (
            availability_status,
            str(representative_item.id),
            representative_item.amount,
            representative_item.unit,
            True,
        )

    async def get_recipe_details(
        self,
        spoonacular_id: int,
        user_id: str,
    ) -> RecipeDetailResponseSchema:
        recipe = await self._get_or_fetch_recipe_details(spoonacular_id)

        inventory_items = await self._load_active_inventory_items(user_id)
        inventory_items_with_names = await self._normalize_inventory_items(inventory_items)

        ingredients: list[RecipeIngredientDetailResponseSchema] = []

        for ingredient in recipe.ingredients:
            matching_items = self._find_matching_inventory_items(
                ingredient_name=ingredient.name,
                inventory_items_with_names=inventory_items_with_names,
            )

            (
                availability_status,
                inventory_item_id,
                inventory_amount,
                inventory_unit,
                is_amount_comparable,
            ) = self._build_ingredient_availability(
                ingredient=ingredient,
                matching_items=matching_items,
            )

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
                    is_amount_comparable=is_amount_comparable,
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

from src.modules.recipes.services import RecipeService


def get_recipe_service() -> RecipeService:
    return RecipeService()

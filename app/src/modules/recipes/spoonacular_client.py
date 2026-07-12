import httpx
from fastapi import HTTPException, status
from src.core.config import settings
from src.core.retry import retry_async

SPOONACULAR_API_URL = 'https://api.spoonacular.com'

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _should_retry(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in RETRYABLE_STATUS_CODES

    return isinstance(error, httpx.TimeoutException | httpx.TransportError)


class SpoonacularClient:
    def _get_api_key(self) -> str:
        if not settings.SPOONACULAR_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Spoonacular API key is not configured',
            )

        return settings.SPOONACULAR_API_KEY

    async def find_recipes_by_ingredients(
        self,
        ingredients: list[str],
        number: int = 10,
    ) -> list[dict]:
        url = f'{SPOONACULAR_API_URL}/recipes/findByIngredients'

        params = {
            'apiKey': self._get_api_key(),
            'ingredients': ','.join(ingredients),
            'number': number,
            'ranking': 1,
            'ignorePantry': True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:

                async def _request() -> httpx.Response:
                    response = await client.get(
                        url,
                        params=params,
                    )
                    response.raise_for_status()
                    return response

                response = await retry_async(
                    _request,
                    attempts=3,
                    retry_exceptions=(httpx.HTTPError,),
                    should_retry=_should_retry,
                )

                data = response.json()

                if not isinstance(data, list):
                    return []

                return data
        except httpx.HTTPStatusError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f'Spoonacular request failed: {error.response.status_code}',
            )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Failed to connect to Spoonacular',
            )

    async def get_recipe_information(
        self,
        recipe_id: int,
    ) -> dict:
        url = f'{SPOONACULAR_API_URL}/recipes/{recipe_id}/information'

        params = {
            'apiKey': self._get_api_key(),
            'includeNutrition': True,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:

                async def _request() -> httpx.Response:
                    response = await client.get(
                        url,
                        params=params,
                    )
                    response.raise_for_status()
                    return response

                response = await retry_async(
                    _request,
                    attempts=3,
                    retry_exceptions=(httpx.HTTPError,),
                    should_retry=_should_retry,
                )

                data = response.json()

                if not isinstance(data, dict):
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail='Invalid Spoonacular response',
                    )

                return data
        except httpx.HTTPStatusError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f'Spoonacular request failed: {error.response.status_code}',
            )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Failed to connect to Spoonacular',
            )

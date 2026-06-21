import httpx

OPEN_FOOD_FACTS_API_URL = 'https://world.openfoodfacts.org/api/v2'
OPEN_FOOD_FACTS_USER_AGENT = 'FoodTrackFYP/1.0'

OPEN_FOOD_FACTS_COUNTRY = 'my'
OPEN_FOOD_FACTS_LANGUAGE = 'en'


def _clean_tags(raw_tags: list[str]) -> list[str]:
    cleaned_tags: list[str] = []

    for tag in raw_tags:
        value = tag.split(':', 1)[-1]

        if value:
            cleaned_tags.append(value.lower())

    return cleaned_tags


async def fetch_product_by_barcode(barcode: str) -> dict | None:
    url = f'{OPEN_FOOD_FACTS_API_URL}/product/{barcode}'

    fields = ','.join(
        [
            'product_name',
            'product_name_en',
            'generic_name',
            'generic_name_en',
            'brands',
            'categories_tags',
            'image_url',
            'image_front_url',
            'image_small_url',
            'image_thumb_url',
            'quantity',
        ]
    )

    headers = {
        'User-Agent': OPEN_FOOD_FACTS_USER_AGENT,
    }

    params = {
        'fields': fields,
        'cc': OPEN_FOOD_FACTS_COUNTRY,
        'lc': OPEN_FOOD_FACTS_LANGUAGE,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(
                url,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return None

    if data.get('status') != 1:
        return None

    product = data.get('product', {})

    image_url = (
        product.get('image_url')
        or product.get('image_front_url')
        or product.get('image_small_url')
        or product.get('image_thumb_url')
    )

    name = (
        product.get('product_name')
        or product.get('product_name_en')
        or product.get('generic_name')
        or product.get('generic_name_en')
    )

    return {
        'barcode': barcode,
        'name': name or None,
        'brand': product.get('brands') or None,
        'tags': _clean_tags(product.get('categories_tags', [])),
        'image_url': image_url or None,
        'quantity': product.get('quantity') or None,
        'source': 'off',
    }

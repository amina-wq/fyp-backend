from datetime import UTC, datetime

from src.modules.categories.models import FoodCategory

DEFAULT_CATEGORIES = [
    {
        'key': 'dairy',
        'name': 'Dairy',
        'description': 'Milk, cheese, yogurt and other dairy products',
        'color_hex': '#EAF6FF',
        'sort_order': 1,
    },
    {
        'key': 'meat',
        'name': 'Meat',
        'description': 'Beef, chicken, lamb and other meat products',
        'color_hex': '#FFECEC',
        'sort_order': 2,
    },
    {
        'key': 'seafood',
        'name': 'Seafood',
        'description': 'Fish, shrimp and other seafood products',
        'color_hex': '#EAF3FF',
        'sort_order': 3,
    },
    {
        'key': 'fruits',
        'name': 'Fruits',
        'description': 'Fresh fruits and fruit products',
        'color_hex': '#FFF1E6',
        'sort_order': 4,
    },
    {
        'key': 'vegetables',
        'name': 'Vegetables',
        'description': 'Fresh vegetables and greens',
        'color_hex': '#EFFFF0',
        'sort_order': 5,
    },
    {
        'key': 'bakery',
        'name': 'Bakery',
        'description': 'Bread, pastries and bakery products',
        'color_hex': '#FFF4E4',
        'sort_order': 6,
    },
    {
        'key': 'grains',
        'name': 'Grains',
        'description': 'Rice, pasta, oats and grain products',
        'color_hex': '#FFF8E1',
        'sort_order': 7,
    },
    {
        'key': 'beverages',
        'name': 'Beverages',
        'description': 'Drinks, juices and other beverages',
        'color_hex': '#EAFBFF',
        'sort_order': 8,
    },
    {
        'key': 'snacks',
        'name': 'Snacks',
        'description': 'Chips, sweets and snack products',
        'color_hex': '#FFF0F8',
        'sort_order': 9,
    },
    {
        'key': 'frozen',
        'name': 'Frozen',
        'description': 'Frozen food products',
        'color_hex': '#EEF7FF',
        'sort_order': 10,
    },
    {
        'key': 'canned',
        'name': 'Canned',
        'description': 'Canned and preserved food',
        'color_hex': '#F2F2F2',
        'sort_order': 11,
    },
    {
        'key': 'cooked_food',
        'name': 'Cooked food',
        'description': 'Prepared and cooked meals',
        'color_hex': '#FFF3EA',
        'sort_order': 12,
    },
    {
        'key': 'leftovers',
        'name': 'Leftovers',
        'description': 'Leftover meals and stored cooked food',
        'color_hex': '#F3F0FF',
        'sort_order': 13,
    },
    {
        'key': 'condiments',
        'name': 'Condiments',
        'description': 'Sauces, dressings and condiments',
        'color_hex': '#FFF7E8',
        'sort_order': 14,
    },
    {
        'key': 'other',
        'name': 'Other',
        'description': 'Other food products',
        'color_hex': '#F5F5F5',
        'sort_order': 99,
    },
]


async def seed_default_categories() -> None:
    for category_data in DEFAULT_CATEGORIES:
        existing_category = await FoodCategory.find_one(
            FoodCategory.key == category_data['key'],
        )

        if existing_category:
            continue

        category = FoodCategory(
            key=category_data['key'],
            name=category_data['name'],
            description=category_data['description'],
            color_hex=category_data['color_hex'],
            icon_url=None,
            is_active=True,
            is_default=True,
            sort_order=category_data['sort_order'],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        await category.insert()

from enum import Enum


class FoodCategory(str, Enum):
    DAIRY = 'dairy'
    MEAT = 'meat'
    SEAFOOD = 'seafood'
    FRUITS = 'fruits'
    VEGETABLES = 'vegetables'
    BAKERY = 'bakery'
    GRAINS = 'grains'
    BEVERAGES = 'beverages'
    SNACKS = 'snacks'
    FROZEN = 'frozen'
    CANNED = 'canned'
    COOKED_FOOD = 'cooked_food'
    LEFTOVERS = 'leftovers'
    CONDIMENTS = 'condiments'
    OTHER = 'other'

# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the storage recommendation service.
# First Written on: Monday, 13-Jul-2026
# Edited on: Monday, 13-Jul-2026

from src.modules.storage_recommendations.services import StorageRecommendationService


def get_storage_recommendation_service() -> StorageRecommendationService:
    return StorageRecommendationService()

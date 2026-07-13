from src.modules.storage_recommendations.services import StorageRecommendationService


def get_storage_recommendation_service() -> StorageRecommendationService:
    return StorageRecommendationService()

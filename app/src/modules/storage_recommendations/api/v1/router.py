# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: API endpoints for food storage duration recommendations.
# First Written on: Monday, 13-Jul-2026
# Edited on: Monday, 13-Jul-2026

from typing import Annotated

from fastapi import APIRouter, Depends
from src.modules.auth.dependencies import JWTBearer
from src.modules.storage_recommendations.dependencies import get_storage_recommendation_service
from src.modules.storage_recommendations.schemas import (
    StorageRecommendationRequestSchema,
    StorageRecommendationResponseSchema,
)
from src.modules.storage_recommendations.services import StorageRecommendationService

router = APIRouter()


@router.post(
    '/recommendations',
    response_model=StorageRecommendationResponseSchema,
    summary='Get a storage duration recommendation for a product without a known expiration date',
)
async def get_storage_recommendation(
    data: StorageRecommendationRequestSchema,
    _: Annotated[dict, Depends(JWTBearer())],
    service: Annotated[StorageRecommendationService, Depends(get_storage_recommendation_service)],
) -> StorageRecommendationResponseSchema:
    return await service.get_recommendation(data)

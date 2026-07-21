# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: API endpoints for push notification settings and test notifications.
# First Written on: Wednesday, 15-Jul-2026
# Edited on: Wednesday, 15-Jul-2026

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from src.modules.auth.dependencies import get_current_user
from src.modules.auth.models import User
from src.modules.notifications.dependencies import get_notification_service
from src.modules.notifications.schemas import TestPushResponseSchema
from src.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    path='/test-push',
    response_model=TestPushResponseSchema,
    status_code=status.HTTP_200_OK,
    summary='Send a test push notification to the current user',
)
async def send_test_push(
    current_user: Annotated[User, Depends(get_current_user)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> TestPushResponseSchema:
    if not current_user.fcm_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='No FCM token registered for this user. Register one via PATCH /auth/fcm-token first.',
        )

    is_sent = await notification_service.send_test_notification(current_user)

    if not is_sent:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Failed to send test push notification. Check server logs and Firebase configuration.',
        )

    logger.info('Test push notification sent: user_id=%s', current_user.id)

    return TestPushResponseSchema(
        sent=True,
        detail='Test push notification sent successfully',
    )

# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: FastAPI dependency providers for the notification service.
# First Written on: Wednesday, 15-Jul-2026
# Edited on: Wednesday, 15-Jul-2026

from src.modules.notifications.service import NotificationService


def get_notification_service() -> NotificationService:
    return NotificationService()

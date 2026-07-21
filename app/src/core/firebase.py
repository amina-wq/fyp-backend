# Programmer Name: Rakhmatullayeva Amina
# Program Name: FoodTrack
# Description: Firebase Cloud Messaging integration for sending push notifications.
# First Written on: Tuesday, 07-Jul-2026
# Edited on: Tuesday, 07-Jul-2026

import asyncio
import logging
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging
from src.core.config import settings

logger = logging.getLogger(__name__)


class FirebaseService:
    _initialized = False

    @classmethod
    def initialize(cls) -> bool:
        if cls._initialized:
            return True

        if not settings.FIREBASE_CREDENTIALS_PATH:
            logger.warning('Firebase credentials path is not configured')
            return False

        credentials_path = Path(settings.FIREBASE_CREDENTIALS_PATH).resolve()

        if not credentials_path.exists():
            logger.error('Firebase credentials file was not found: %s', credentials_path)
            return False

        try:
            firebase_admin.get_app()
            cls._initialized = True
            logger.info('Firebase already initialized')
            return True
        except ValueError:
            pass

        try:
            firebase_credentials = credentials.Certificate(str(credentials_path))
            firebase_admin.initialize_app(firebase_credentials)
            cls._initialized = True
            logger.info('Firebase initialized successfully')
            return True
        except Exception:
            logger.exception('Failed to initialize Firebase')
            return False

    @classmethod
    async def send_push_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> bool:
        if not token:
            return False

        if not cls.initialize():
            return False

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
        )

        try:
            await asyncio.to_thread(messaging.send, message)
            logger.info('Push notification sent successfully')
            return True
        except Exception:
            logger.exception('Failed to send push notification')
            return False

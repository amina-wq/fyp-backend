import asyncio
import logging

from src.core.config import settings
from src.core.firebase import FirebaseService
from src.core.logger import setup_logging
from src.database.data_storage import close_database, init_database
from src.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)

setup_logging()


async def run_notification_worker() -> None:
    logger.info('Starting notification worker')

    await init_database()
    FirebaseService.initialize()

    notification_service = NotificationService()

    try:
        while True:
            try:
                result = await notification_service.process_due_notifications()
                logger.info(
                    'Notification worker cycle completed: processed=%s sent=%s skipped=%s failed=%s',
                    result['processed'],
                    result['sent'],
                    result['skipped'],
                    result['failed'],
                )
            except Exception:
                logger.exception('Notification worker cycle failed')

            await asyncio.sleep(settings.NOTIFICATION_WORKER_INTERVAL_SECONDS)

    finally:
        await close_database()
        logger.info('Notification worker stopped')


def main() -> None:
    asyncio.run(run_notification_worker())


if __name__ == '__main__':
    main()

import logging
from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from src.core.config import settings
from src.modules.auth.models import User
from src.modules.products.models import Product


logger = logging.getLogger(__name__)

class Database:
    client: AsyncMongoClient | None = None
    database: AsyncDatabase | None = None


db = Database()


async def init_database() -> None:
    logger.info("Initializing MongoDB connection")

    db.client = AsyncMongoClient(settings.MONGODB_URL)
    db.database = db.client[settings.MONGODB_DB_NAME]

    logger.info("Initializing Beanie document models")

    await init_beanie(
        database=db.database,
        document_models=[
            User,
            Product,

        ],
    )

    logger.info("Database initialization completed")

async def close_database() -> None:
    if db.client:
        await db.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncDatabase:
    if db.database is None:
        raise RuntimeError("Database is not initialized")
    return db.database
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from src.api.v1.router import router as api_v1_router
from src.core.config import settings
from src.core.logger import setup_logging
from src.database.data_storage import close_database, init_database
from src.modules.categories.seed import seed_default_categories

logger = logging.getLogger(__name__)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting FoodTrack API')
    await init_database()
    await seed_default_categories()
    logger.info('Application startup completed')

    yield

    logger.info('Shutting down FoodTrack API')
    await close_database()
    logger.info('Application shutdown completed')


app = FastAPI(
    title='FoodTrack API',
    description='Cross-platform mobile app for automated food expiration tracking',
    version='1.0.0',
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    lifespan=lifespan,
)


@app.get('/api/health')
async def health_check():
    return {'status': 'ok', 'message': 'FoodTrack API is running'}


app.include_router(api_v1_router)


if __name__ == '__main__':
    uvicorn.run(
        app,
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        use_colors=True,
    )

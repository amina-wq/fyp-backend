import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from src.core.config import settings
from src.core.logger import setup_logging
from src.database.data_storage import close_database, init_database
from src.modules.auth.api.v1.router import router as auth_router

logger = logging.getLogger(__name__)

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting FoodTrack API')
    await init_database()
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


app.include_router(
    auth_router,
    prefix='/api/v1/auth',
    tags=['Auth'],
)


if __name__ == '__main__':
    uvicorn.run(
        app,
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        use_colors=True,
    )

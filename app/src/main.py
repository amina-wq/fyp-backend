import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database.data_storage import init_database, close_database
from src.modules.auth.api.v1.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield
    await close_database()


app = FastAPI(
    title="FoodTrack API",
    description="Cross-platform mobile app for automated food expiration tracking",
    version="1.0.0",
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "FoodTrack API is running"}


app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Auth"],
)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
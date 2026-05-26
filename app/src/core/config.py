from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    FASTAPI_HOST: str = "0.0.0.0"
    FASTAPI_PORT: int = 80
    FASTAPI_WORKERS: int = 4

    MONGODB_URL: str
    MONGODB_DB_NAME: str = "foodtrack_db"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra="ignore",
    )


settings = Settings()
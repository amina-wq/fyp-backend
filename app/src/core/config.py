from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / '.env'


class Settings(BaseSettings):
    FASTAPI_HOST: str = '0.0.0.0'
    FASTAPI_PORT: int = 80
    FASTAPI_WORKERS: int = 4

    MONGODB_URL: str
    MONGODB_DB_NAME: str = 'foodtrack_db'

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = 'HS256'
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    LOGGING_LEVEL: str = 'INFO'

    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_REGION: str
    AWS_S3_BUCKET_NAME: str
    AWS_S3_PUBLIC_BASE_URL: str

    SPOONACULAR_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        extra='ignore',
    )


settings = Settings()

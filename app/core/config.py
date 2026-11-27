from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REDIS_URL,
    SECRET_KEY_MIN_LENGTH,
)


class Settings(BaseSettings):
    DATABASE_URL: str
    DB_ECHO: bool = False
    REDIS_TIMEOUT_SECONDS: float = Field(default=0.25, gt=0, allow_inf_nan=False)
    REDIS_URL: str = DEFAULT_REDIS_URL
    CACHE_TTL_SECONDS: int = Field(DEFAULT_CACHE_TTL_SECONDS, ge=1)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        DEFAULT_LOG_LEVEL
    )

    SECRET_KEY: str = Field(min_length=SECRET_KEY_MIN_LENGTH)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

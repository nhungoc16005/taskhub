import os
from pathlib import Path
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.core import messages
from app.core.constants import (
    DEFAULT_APP_ENV,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_REDIS_URL,
    ENV_FILES,
    PRODUCTION_SECRET_MIN_UNIQUE_CHARACTERS,
    SAMPLE_SECRET_MARKERS,
    SECRET_KEY_MIN_LENGTH,
)


class Settings(BaseSettings):
    APP_ENV: Literal["dev", "test", "prod"] = DEFAULT_APP_ENV
    DOCS_ENABLED: bool | None = None
    DATABASE_URL: str
    DB_ECHO: bool = False
    REDIS_URL: str = DEFAULT_REDIS_URL
    CACHE_TTL_SECONDS: int = Field(DEFAULT_CACHE_TTL_SECONDS, ge=1)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = (
        DEFAULT_LOG_LEVEL
    )

    SECRET_KEY: str = Field(min_length=SECRET_KEY_MIN_LENGTH, repr=False)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, ge=1)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1)

    model_config = SettingsConfigDict(
        extra="ignore", env_file_encoding="utf-8", hide_input_in_errors=True
    )

    def __init__(self, **values):
        app_env = values.get("APP_ENV", os.getenv("APP_ENV", DEFAULT_APP_ENV))
        if "_env_file" not in values:
            env_file = ENV_FILES.get(app_env)
            if app_env == "dev" and not Path(env_file).is_file():
                env_file = ".env"
            values["_env_file"] = env_file
        values["APP_ENV"] = app_env
        super().__init__(**values)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str, info: ValidationInfo) -> str:
        try:
            url = make_url(value)
            if (
                url.drivername == "sqlite+aiosqlite"
                and info.data.get("APP_ENV") == "test"
            ):
                return value
            if (
                url.drivername != "postgresql+asyncpg"
                or any(char.isspace() for char in value)
                or not all((url.host, url.database, url.username, url.password))
                or (url.port is not None and not 1 <= url.port <= 65535)
            ):
                raise ValueError(messages.INVALID_DATABASE_URL)
        except (ArgumentError, ValueError) as exc:
            raise ValueError(messages.INVALID_DATABASE_URL) from exc
        return value

    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        try:
            url = urlsplit(value)
            database = url.path.removeprefix("/")
            if (
                url.scheme not in {"redis", "rediss"}
                or not url.hostname
                or any(char.isspace() for char in value)
                or (url.port is not None and not 1 <= url.port <= 65535)
                or (database and not database.isdecimal())
                or url.query
                or url.fragment
            ):
                raise ValueError(messages.INVALID_REDIS_URL)
        except ValueError as exc:
            raise ValueError(messages.INVALID_REDIS_URL) from exc
        return value

    @model_validator(mode="after")
    def validate_environment(self) -> Self:
        if self.APP_ENV == "prod":
            if (
                any(
                    marker in self.SECRET_KEY.lower()
                    for marker in SAMPLE_SECRET_MARKERS
                )
                or len(set(self.SECRET_KEY)) < PRODUCTION_SECRET_MIN_UNIQUE_CHARACTERS
            ):
                raise ValueError(messages.PRODUCTION_SECRET_WEAK)
            if self.DB_ECHO:
                raise ValueError(messages.PRODUCTION_DB_ECHO)
            if "REDIS_URL" not in self.model_fields_set:
                raise ValueError(messages.PRODUCTION_REDIS_REQUIRED)
        if self.DOCS_ENABLED is None:
            self.DOCS_ENABLED = self.APP_ENV != "prod"
        return self


settings = Settings()

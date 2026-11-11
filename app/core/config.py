from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import SECRET_KEY_MIN_LENGTH


class Settings(BaseSettings):
    DATABASE_URL: str
    DB_ECHO: bool = False

    SECRET_KEY: str = Field(min_length=SECRET_KEY_MIN_LENGTH)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

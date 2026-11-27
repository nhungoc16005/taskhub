from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, settings


def build_engine(config: Settings) -> AsyncEngine:
    """Each worker owns one bounded PostgreSQL pool; SQLite uses its own defaults."""
    if make_url(config.DATABASE_URL).get_backend_name() == "postgresql":
        return create_async_engine(
            config.DATABASE_URL,
            echo=config.DB_ECHO,
            pool_pre_ping=True,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
            pool_timeout=config.DB_POOL_TIMEOUT_SECONDS,
            pool_recycle=config.DB_POOL_RECYCLE_SECONDS,
        )
    return create_async_engine(config.DATABASE_URL, echo=config.DB_ECHO)


engine = build_engine(settings)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

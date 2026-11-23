from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.api.v1.router import api_router
from app.core.cache import TaskCache
from app.core.config import settings
from app.core.constants import REDIS_TIMEOUT_SECONDS
from app.core.database import engine
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
        socket_timeout=REDIS_TIMEOUT_SECONDS,
        retry=Retry(NoBackoff(), 0),
    )
    app.state.task_cache = TaskCache(redis, settings.CACHE_TTL_SECONDS)
    try:
        yield
    finally:
        try:
            await redis.aclose()
        finally:
            await engine.dispose()


configure_logging(settings.LOG_LEVEL)
app = FastAPI(
    title="TaskHub",
    lifespan=lifespan,
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
)
app.add_middleware(RequestLoggingMiddleware)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}

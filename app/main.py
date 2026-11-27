from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.api.documentation import API_DESCRIPTION, OPENAPI_TAGS
from app.api.v1.router import api_router
from app.core.cache import TaskCache
from app.core.config import settings
from app.core.constants import API_TITLE, API_VERSION
from app.core.database import engine
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
        socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
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


def create_app() -> FastAPI:
    configure_logging(settings.LOG_LEVEL)
    application = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
        docs_url="/docs" if settings.DOCS_ENABLED else None,
        redoc_url="/redoc" if settings.DOCS_ENABLED else None,
        openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
        swagger_ui_parameters={"persistAuthorization": False},
    )
    application.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router, prefix="/api/v1")
    application.add_api_route(
        "/health", health, tags=["health"], summary="Check API liveness"
    )
    return application


async def health():
    return {"status": "ok"}


app = create_app()

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-test-secret-key-1234567890")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import event, update  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, User, UserRole  # noqa: E402

PASSWORD = "12345678"


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def register(client):
    async def _register(email="a@x.com", name="Ann", password=PASSWORD):
        return await client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": name, "password": password},
        )

    return _register


@pytest_asyncio.fixture
async def login(client):
    async def _login(email="a@x.com", password=PASSWORD):
        return await client.post(
            "/api/v1/auth/login", data={"username": email, "password": password}
        )

    return _login


@pytest_asyncio.fixture
async def make_user(register, login, session_factory):
    """Đăng ký + đăng nhập, trả về (user_json, tokens). admin=True để nâng quyền."""

    async def _make(email="a@x.com", admin=False):
        user = (await register(email=email)).json()
        if admin:
            async with session_factory() as s:
                await s.execute(
                    update(User)
                    .where(User.id == user["id"])
                    .values(role=UserRole.ADMIN)
                )
                await s.commit()
        tokens = (await login(email=email)).json()
        return user, tokens

    return _make


def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}

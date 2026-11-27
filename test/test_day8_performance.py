import asyncio
import importlib.util
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError
from sqlalchemy import create_engine, event, inspect, text

from app.core import database, security
from app.core.config import Settings
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.schemas.common import Pagination
from app.schemas.task import TaskRead
from app.schemas.workspace import MemberRead


@pytest.mark.parametrize("operation", ["hash", "verify"])
async def test_password_work_does_not_block_event_loop(monkeypatch, operation):
    loop_thread = threading.get_ident()
    started, release = threading.Event(), threading.Event()
    worker_threads = []

    def blocking(*args):
        worker_threads.append(threading.get_ident())
        started.set()
        if not release.wait(2):
            raise AssertionError("event loop could not release the bcrypt worker")
        return "hashed" if operation == "hash" else True

    monkeypatch.setattr(
        security,
        "hash_password" if operation == "hash" else "verify_password",
        blocking,
    )
    task = asyncio.create_task(
        security.hash_password_async("password")
        if operation == "hash"
        else security.verify_password_async("password", "hashed")
    )
    try:
        async with asyncio.timeout(1):
            while not started.is_set():
                await asyncio.sleep(0.001)
        assert worker_threads == [worker_threads[0]]
        assert worker_threads[0] != loop_thread
    finally:
        release.set()
        result = await task
    assert result == ("hashed" if operation == "hash" else True)


async def test_auth_endpoints_use_threaded_bcrypt(client, monkeypatch):
    loop_thread = threading.get_ident()
    calls = []
    for name in ("hash_password", "verify_password"):
        original = getattr(security, name)

        def record(*args, original=original, name=name):
            calls.append((name, threading.get_ident()))
            return original(*args)

        monkeypatch.setattr(security, name, record)
    account = {
        "email": "threads@example.com",
        "password": "Password123!",
        "full_name": "Threads",
    }
    assert (await client.post("/api/v1/auth/register", json=account)).status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": account["email"], "password": account["password"]},
    )
    assert login.status_code == 200
    changed = await client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": "Bearer " + login.json()["access_token"]},
        json={"current_password": account["password"], "new_password": "Changed123!"},
    )
    assert changed.status_code == 204
    assert [name for name, _ in calls].count("hash_password") == 2
    assert [name for name, _ in calls].count("verify_password") == 3
    assert all(thread != loop_thread for _, thread in calls)


def config(**values):
    return Settings(
        _env_file=None,
        APP_ENV="test",
        DATABASE_URL="postgresql+asyncpg://user:pass@db/taskhub",
        SECRET_KEY="test-secret-key-12345678901234567890",
        **values,
    )


def test_postgres_pool_settings_are_applied(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(database, "create_async_engine", factory)
    settings = config(
        DB_POOL_SIZE=3,
        DB_MAX_OVERFLOW=2,
        DB_POOL_TIMEOUT_SECONDS=4.5,
        DB_POOL_RECYCLE_SECONDS=600,
    )
    database.build_engine(settings)
    factory.assert_called_once_with(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_timeout=4.5,
        pool_recycle=600,
    )


def test_sqlite_does_not_receive_postgres_pool_options(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(database, "create_async_engine", factory)
    settings = config()
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    database.build_engine(settings)
    factory.assert_called_once_with(settings.DATABASE_URL, echo=False)


@pytest.mark.parametrize(
    "values",
    [
        {"DB_POOL_SIZE": 0},
        {"DB_MAX_OVERFLOW": -1},
        {"DB_POOL_TIMEOUT_SECONDS": 0},
        {"DB_POOL_TIMEOUT_SECONDS": float("inf")},
        {"DB_POOL_RECYCLE_SECONDS": 0},
    ],
)
def test_pool_config_rejects_unbounded_or_invalid_values(values):
    with pytest.raises(ValidationError):
        config(**values)


@pytest.mark.parametrize("count", [1, 12])
async def test_task_page_query_count_is_constant(session_factory, team, count):
    async with session_factory() as session:
        session.add_all(
            Task(
                project_id=team["project"]["id"],
                created_by=team["people"]["owner"]["user"]["id"],
                title=f"Task {i}",
            )
            for i in range(count)
        )
        await session.commit()
    queries = []
    async with session_factory() as session:
        engine = session.bind.sync_engine

        def record(conn, cursor, statement, parameters, context, many):
            queries.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            repo = TaskRepository(session)
            rows = await repo.list_by_project(team["project"]["id"], Pagination(0, 100))
            assert await repo.count_by_project(team["project"]["id"]) == count
            assert len([TaskRead.model_validate(row) for row in rows]) == count
        finally:
            event.remove(engine, "before_cursor_execute", record)
    assert len(queries) == 2


async def test_members_eager_load_users_in_two_queries(
    session_factory, team, make_user, client
):
    workspace_id = team["workspace"]["id"]
    for i in range(5):
        user, _ = await make_user(email=f"member{i}@example.com")
        assert (
            await client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                headers=team["people"]["owner"]["headers"],
                json={"email": user["email"], "role": "VIEWER"},
            )
        ).status_code == 201
    queries = []
    async with session_factory() as session:
        engine = session.bind.sync_engine

        def record(conn, cursor, statement, parameters, context, many):
            queries.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            members = await WorkspaceMemberRepository(session).list_by_workspace(
                workspace_id
            )
            assert len([MemberRead.model_validate(row) for row in members]) == 8
        finally:
            event.remove(engine, "before_cursor_execute", record)
    assert len(queries) == 2


def test_task_index_upgrade_query_plan_and_downgrade():
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/e5b7218cf012_task_composite_index.py"
    )
    spec = importlib.util.spec_from_file_location("day8_index", path)
    revision = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revision)
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE tasks (id INTEGER PRIMARY KEY, project_id INTEGER, status TEXT, priority TEXT)"
                )
            )
            conn.execute(text("INSERT INTO tasks VALUES (1, 1, 'TODO', 'HIGH')"))
            revision.op = Operations(MigrationContext.configure(conn))
            revision.upgrade()
            index = inspect(conn).get_indexes("tasks")[0]
            assert index["column_names"] == ["project_id", "status", "priority", "id"]
            plan = conn.exec_driver_sql(
                "EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE project_id=1 AND status='TODO' AND priority='HIGH' ORDER BY id LIMIT 10"
            ).all()
            assert "ix_tasks_project_status_priority_id" in str(plan)
            assert "TEMP B-TREE" not in str(plan)
            revision.downgrade()
            assert inspect(conn).get_indexes("tasks") == []
            assert conn.execute(text("SELECT count(*) FROM tasks")).scalar_one() == 1
    finally:
        engine.dispose()

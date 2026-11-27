import logging
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError
from test_day5 import create_task

from app.api.deps import get_email_service
from app.core import messages
from app.core.config import Settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.main import app, lifespan
from app.repositories.task_repository import TaskRepository
from app.schemas.common import Pagination
from app.services.email_service import EmailService


@pytest.fixture
def task_reads(monkeypatch):
    calls = []
    original = TaskRepository.list_by_project

    async def record(repo, *args, **kwargs):
        calls.append((args, kwargs))
        return await original(repo, *args, **kwargs)

    monkeypatch.setattr(TaskRepository, "list_by_project", record)
    return calls


@pytest.fixture
def email_delivery():
    service = EmailService()
    service.send_assignment = AsyncMock()
    app.dependency_overrides[get_email_service] = lambda: service
    yield service.send_assignment
    app.dependency_overrides.pop(get_email_service, None)


def task_list(team):
    return f"/api/v1/projects/{team['project']['id']}/tasks"


def owner_headers(team):
    return team["people"]["owner"]["headers"]


async def test_cache_miss_then_hit(client, team, task_reads, task_cache):
    task = await create_task(client, team)
    path, headers = task_list(team), owner_headers(team)
    first = await client.get(path, headers=headers)
    second = await client.get(path, headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()["items"][0]["id"] == task["id"]
    assert len(task_reads) == 1
    lookup = await task_cache.lookup(
        team["project"]["id"], Pagination(0, 10), None, None, None
    )
    assert 0 < await task_cache.redis.ttl(lookup.key) <= task_cache.ttl
    assert "hashed_password" not in lookup.payload


@pytest.mark.parametrize(
    "params",
    [
        {"status": "DONE"},
        {"priority": "HIGH"},
        {"assignee_id": 1},
        {"skip": 1},
        {"limit": 1},
        [("status", "TODO"), ("status", "DONE"), ("priority", "HIGH")],
    ],
)
async def test_cache_separates_filters_and_pages(client, team, task_reads, params):
    await create_task(client, team)
    path, headers = task_list(team), owner_headers(team)
    assert (await client.get(path, headers=headers)).status_code == 200
    first = await client.get(path, headers=headers, params=params)
    second = await client.get(path, headers=headers, params=params)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(task_reads) == 2


async def test_cache_canonical_filters_and_project_isolation(client, team, task_reads):
    path, headers = task_list(team), owner_headers(team)
    await create_task(client, team)
    first = await client.get(
        path, headers=headers, params=[("status", "TODO"), ("status", "DONE")]
    )
    second = await client.get(
        path,
        headers=headers,
        params=[("status", "DONE"), ("status", "TODO"), ("status", "TODO")],
    )
    assert first.json() == second.json()
    assert len(task_reads) == 1
    project = (
        await client.post(
            f"/api/v1/workspaces/{team['workspace']['id']}/projects",
            headers=headers,
            json={"name": "Other"},
        )
    ).json()
    result = await client.get(
        f"/api/v1/projects/{project['id']}/tasks", headers=headers
    )
    assert result.json()["total"] == 0
    assert len(task_reads) == 2


@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_task_writes_invalidate_all_cached_pages(
    client, team, task_reads, operation
):
    task = await create_task(client, team)
    path, headers = task_list(team), owner_headers(team)
    await client.get(path, headers=headers)
    await client.get(path, headers=headers, params={"priority": "HIGH"})
    if operation == "create":
        response = await client.post(
            path, headers=headers, json={"title": "Second", "priority": "HIGH"}
        )
        assert response.status_code == 201
    elif operation == "update":
        response = await client.patch(
            f"/api/v1/tasks/{task['id']}", headers=headers, json={"priority": "HIGH"}
        )
        assert response.status_code == 200
    else:
        assert (
            await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
        ).status_code == 204
    all_tasks = (await client.get(path, headers=headers)).json()
    filtered = (
        await client.get(path, headers=headers, params={"priority": "HIGH"})
    ).json()
    assert all_tasks["total"] == {"create": 2, "update": 1, "delete": 0}[operation]
    assert filtered["total"] == (0 if operation == "delete" else 1)
    assert len(task_reads) == 4


async def test_authorization_precedes_cache_and_revocation(
    client, team, task_reads, task_cache, monkeypatch
):
    task = await create_task(client, team)
    path, headers = task_list(team), owner_headers(team)
    await client.get(path, headers=headers)
    lookup = AsyncMock(wraps=task_cache.lookup)
    monkeypatch.setattr(task_cache, "lookup", lookup)
    outsider = team["people"]["outsider"]["headers"]
    assert (await client.get(path, headers=outsider)).status_code == 404
    assert (await client.get(path)).status_code == 401
    viewer = team["people"]["viewer"]
    assert (
        await client.patch(
            f"/api/v1/tasks/{task['id']}",
            headers=viewer["headers"],
            json={"title": "No"},
        )
    ).status_code == 403
    assert lookup.await_count == 0
    assert (await client.get(path, headers=viewer["headers"])).status_code == 200
    await client.delete(
        f"/api/v1/workspaces/{team['workspace']['id']}/members/{viewer['user']['id']}",
        headers=headers,
    )
    lookup.reset_mock()
    assert (await client.get(path, headers=viewer["headers"])).status_code == 404
    assert lookup.await_count == 0 and len(task_reads) == 1


@pytest.mark.parametrize("operation", ["get", "set", "incr"])
async def test_redis_failures_fall_back_without_breaking_writes(
    client, team, task_cache, task_reads, monkeypatch, caplog, operation
):
    task = await create_task(client, team)
    path, headers = task_list(team), owner_headers(team)
    await client.get(path, headers=headers)
    if operation == "set":
        await task_cache.invalidate(team["project"]["id"])
    original = getattr(task_cache.redis, operation)
    monkeypatch.setattr(
        task_cache.redis,
        operation,
        AsyncMock(side_effect=RedisConnectionError("unavailable")),
    )
    with caplog.at_level(logging.WARNING):
        if operation == "incr":
            response = await client.patch(
                f"/api/v1/tasks/{task['id']}",
                headers=headers,
                json={"title": "Updated"},
            )
            assert response.status_code == 200
        result = await client.get(path, headers=headers)
    assert result.status_code == 200 and result.json()["total"] == 1
    assert len(task_reads) == 2
    assert "using database" in caplog.text
    if operation == "incr":
        monkeypatch.setattr(task_cache.redis, operation, original)
        recovered = await client.get(path, headers=headers)
        assert recovered.json()["items"][0]["title"] == "Updated"


async def test_invalid_cache_payload_falls_back(
    client, team, task_cache, task_reads, caplog
):
    path, headers = task_list(team), owner_headers(team)
    await client.get(path, headers=headers)
    lookup = await task_cache.lookup(
        team["project"]["id"], Pagination(0, 10), None, None, None
    )
    await task_cache.redis.set(lookup.key, "not-json")
    with caplog.at_level(logging.WARNING):
        result = await client.get(path, headers=headers)
    assert result.status_code == 200 and len(task_reads) == 2
    assert messages.CACHE_INVALID_PAYLOAD in caplog.text


async def test_inflight_old_page_cannot_replace_new_generation(task_cache):
    old = await task_cache.lookup(1, Pagination(0, 10), None, None, None)
    await task_cache.invalidate(1)
    await task_cache.store(old, "old page")
    current = await task_cache.lookup(1, Pagination(0, 10), None, None, None)
    assert old.key != current.key and current.payload is None


async def test_removing_assignee_invalidates_cached_tasks(client, team, task_cache):
    editor = team["people"]["editor"]["user"]["id"]
    await create_task(client, team, assignee_id=editor)
    path, headers = task_list(team), owner_headers(team)
    assert (
        await client.get(path, headers=headers, params={"assignee_id": editor})
    ).json()["total"] == 1
    await client.get(path, headers=headers)
    assert (
        await client.delete(
            f"/api/v1/workspaces/{team['workspace']['id']}/members/{editor}",
            headers=headers,
        )
    ).status_code == 204
    assert (
        await client.get(path, headers=headers, params={"assignee_id": editor})
    ).json()["total"] == 0
    assert (await client.get(path, headers=headers)).json()["items"][0][
        "assignee_id"
    ] is None


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("create_other", 1),
        ("assign_unassigned", 1),
        ("change_assignee", 1),
        ("create_unassigned", 0),
        ("create_self", 0),
        ("same_assignee", 0),
        ("unassign", 0),
        ("update_title", 0),
        ("assign_self", 0),
    ],
)
async def test_assignment_email_rules(client, team, email_delivery, scenario, expected):
    path, headers = task_list(team), owner_headers(team)
    owner = team["people"]["owner"]["user"]["id"]
    editor = team["people"]["editor"]["user"]["id"]
    viewer = team["people"]["viewer"]["user"]["id"]
    if scenario.startswith("create_"):
        payload = {"title": "Created"}
        if scenario != "create_unassigned":
            payload["assignee_id"] = owner if scenario == "create_self" else viewer
        response = await client.post(path, headers=headers, json=payload)
        assert response.status_code == 201
    else:
        initial = None if scenario == "assign_unassigned" else editor
        task = await create_task(client, team, role="owner", assignee_id=initial)
        email_delivery.reset_mock()
        payload = (
            {
                "assignee_id": {
                    "assign_unassigned": viewer,
                    "change_assignee": viewer,
                    "same_assignee": editor,
                    "unassign": None,
                    "assign_self": owner,
                }.get(scenario)
            }
            if scenario != "update_title"
            else {"title": "Updated"}
        )
        response = await client.patch(
            f"/api/v1/tasks/{task['id']}", headers=headers, json=payload
        )
        assert response.status_code == 200
    assert email_delivery.await_count == expected
    if expected:
        email_delivery.assert_awaited_once_with(
            team["people"]["viewer"]["user"]["id"],
            response.json()["id"],
        )


async def test_background_email_runs_after_response(client, team, email_delivery):
    completed = []

    async def send_email(*args):
        assert completed == [True]

    email_delivery.side_effect = send_email

    async def observed(scope, receive, send):
        async def track(message):
            if message["type"] == "http.response.body" and not message.get(
                "more_body", False
            ):
                completed.append(True)
            await send(message)

        await app(scope, receive, track)

    async with AsyncClient(
        transport=ASGITransport(app=observed), base_url="http://test"
    ) as observer:
        response = await observer.post(
            task_list(team),
            headers=owner_headers(team),
            json={
                "title": "Background",
                "assignee_id": team["people"]["viewer"]["user"]["id"],
            },
        )
    assert response.status_code == 201 and email_delivery.await_count == 1


async def test_failed_transaction_neither_invalidates_nor_emails(
    client, team, email_delivery, task_cache, monkeypatch
):
    version = await task_cache._version(team["project"]["id"])
    original = TaskRepository.create

    async def fail_after_flush(repo, data):
        await original(repo, data)
        raise RuntimeError("rollback")

    monkeypatch.setattr(TaskRepository, "create", fail_after_flush)
    with pytest.raises(RuntimeError, match="rollback"):
        await client.post(
            task_list(team),
            headers=owner_headers(team),
            json={
                "title": "Rollback",
                "assignee_id": team["people"]["viewer"]["user"]["id"],
            },
        )
    assert await task_cache._version(team["project"]["id"]) == version
    assert (await client.get(task_list(team), headers=owner_headers(team))).json()[
        "total"
    ] == 0
    email_delivery.assert_not_awaited()


async def test_email_failure_is_logged_without_failing_response(
    client, team, email_delivery, caplog
):
    email_delivery.side_effect = RuntimeError("mail unavailable")
    with caplog.at_level(logging.ERROR):
        response = await client.post(
            task_list(team),
            headers=owner_headers(team),
            json={
                "title": "Committed",
                "assignee_id": team["people"]["viewer"]["user"]["id"],
            },
        )
    assert response.status_code == 201
    assert "Assignment email failed" in caplog.text


@pytest.mark.parametrize("request_id", [None, "client-request-123"])
async def test_request_id_and_access_log(client, caplog, request_id):
    headers = {"X-Request-ID": request_id} if request_id else {}
    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = await client.get("/health", headers=headers)
    actual = response.headers["X-Request-ID"]
    if request_id:
        assert actual == request_id
    else:
        assert str(UUID(actual)) == actual
    record = next(r for r in caplog.records if r.name == "app.core.middleware")
    assert (record.method, record.path, record.status_code) == ("GET", "/health", 200)
    assert record.request_id == actual and record.duration_ms >= 0


async def test_unexpected_error_is_generic_and_correlated(caplog):
    isolated = FastAPI()
    register_exception_handlers(isolated)
    isolated.add_middleware(RequestLoggingMiddleware)

    @isolated.get("/boom")
    async def boom():
        raise RuntimeError("private-database-details")

    with caplog.at_level(logging.INFO):
        async with AsyncClient(
            transport=ASGITransport(app=isolated, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get("/boom", headers={"X-Request-ID": "error-123"})
    assert response.status_code == 500
    assert response.json() == {"detail": messages.INTERNAL_SERVER_ERROR}
    assert response.headers["X-Request-ID"] == "error-123"
    assert "private-database-details" not in response.text
    errors = [r for r in caplog.records if r.name == "app.core.error_handlers"]
    assert errors == []  # Uvicorn owns traceback logging after the ASGI re-raise.
    assert any(getattr(r, "status_code", None) == 500 for r in caplog.records)


async def test_handled_errors_keep_headers(client):
    response = await client.get(
        "/api/v1/workspaces", headers={"X-Request-ID": "unauthorized"}
    )
    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_logging_configuration_and_settings():
    configured = Settings(
        _env_file=None, DATABASE_URL="sqlite+aiosqlite://", SECRET_KEY="x" * 32
    )
    assert configured.CACHE_TTL_SECONDS == 60
    assert configured.LOG_LEVEL == "INFO"
    original = logging.getLogger().level
    try:
        configure_logging("WARNING")
        assert logging.getLogger().level == logging.WARNING
    finally:
        logging.getLogger().setLevel(original)


async def test_lifespan_redis_connection_failure_and_cleanup(monkeypatch, caplog):
    from redis.asyncio.connection import Connection

    from app.core.database import engine

    connect = AsyncMock(side_effect=OSError("Redis is offline"))
    dispose = AsyncMock()
    monkeypatch.setattr(Connection, "_connect", connect)
    monkeypatch.setattr(type(engine), "dispose", dispose)
    isolated = FastAPI()
    with caplog.at_level(logging.WARNING):
        async with lifespan(isolated):
            cache = isolated.state.task_cache
            close = AsyncMock(wraps=cache.redis.aclose)
            monkeypatch.setattr(cache.redis, "aclose", close)
            result = await cache.lookup(
                1, Pagination(skip=0, limit=20), None, None, None
            )
            assert result.key is None and result.payload is None
            connect.assert_awaited_once()
    close.assert_awaited_once()
    dispose.assert_awaited_once()
    assert "Task cache unavailable" in caplog.text

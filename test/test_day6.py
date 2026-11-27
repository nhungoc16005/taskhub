import logging
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from test_day5 import create_task

from app.core import messages
from app.repositories.task_repository import TaskRepository
from app.schemas.common import Pagination


@pytest.fixture
def task_reads(monkeypatch):
    calls = []
    original = TaskRepository.list_by_project

    async def record(repo, *args, **kwargs):
        calls.append((args, kwargs))
        return await original(repo, *args, **kwargs)

    monkeypatch.setattr(TaskRepository, "list_by_project", record)
    return calls

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

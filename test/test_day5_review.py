from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from test_day5 import create_task

from app.core import messages
from app.main import app
from app.models.task import Task
from app.models.workspace import WorkspaceMember
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository


async def test_demoted_author_cannot_delete_task_or_comment(client, team):
    task = await create_task(client, team)
    editor = team["people"]["editor"]
    owner = team["people"]["owner"]["headers"]
    path = f"/api/v1/tasks/{task['id']}"
    comment = (
        await client.post(
            path + "/comments", headers=editor["headers"], json={"content": "Keep this"}
        )
    ).json()
    response = await client.patch(
        f"/api/v1/workspaces/{team['workspace']['id']}/members/{editor['user']['id']}",
        headers=owner,
        json={"role": "VIEWER"},
    )
    assert response.status_code == 200
    assert (await client.delete(path, headers=editor["headers"])).status_code == 403
    assert (
        await client.delete(
            f"/api/v1/comments/{comment['id']}", headers=editor["headers"]
        )
    ).status_code == 403
    assert (await client.get(path, headers=owner)).status_code == 200
    assert (await client.get(path + "/comments", headers=owner)).json()["total"] == 1


@pytest.mark.parametrize("role", ["owner", "editor", "admin"])
async def test_archived_project_blocks_all_resource_writes(client, team, role):
    task = await create_task(client, team)
    owner = team["people"]["owner"]["headers"]
    project = f"/api/v1/projects/{team['project']['id']}"
    task_path = f"/api/v1/tasks/{task['id']}"
    label = (
        await client.post(project + "/labels", headers=owner, json={"name": "Bug"})
    ).json()
    label_path = f"/api/v1/labels/{label['id']}"
    link = task_path + f"/labels/{label['id']}"
    assert (await client.post(link, headers=owner)).status_code == 201
    comment = (
        await client.post(
            task_path + "/comments", headers=owner, json={"content": "Keep"}
        )
    ).json()
    assert (await client.post(project + "/archive", headers=owner)).status_code == 200
    headers = team["people"][role]["headers"]
    writes = [
        ("POST", project + "/tasks", {"title": "No"}),
        ("PATCH", task_path, {"title": "No"}),
        ("DELETE", task_path, None),
        ("POST", project + "/labels", {"name": "No"}),
        ("PATCH", label_path, {"name": "No"}),
        ("DELETE", label_path, None),
        ("POST", link, None),
        ("DELETE", link, None),
        ("POST", task_path + "/comments", {"content": "No"}),
        ("DELETE", f"/api/v1/comments/{comment['id']}", None),
        ("PATCH", project, {"name": "No"}),
    ]
    for method, path, payload in writes:
        response = await client.request(method, path, headers=headers, json=payload)
        assert response.status_code == 409, (method, path, response.text)
        assert response.json()["detail"] == messages.PROJECT_ARCHIVED
    viewer = team["people"]["viewer"]["headers"]
    for path in (
        project,
        task_path,
        project + "/tasks",
        project + "/labels",
        task_path + "/comments",
        task_path + "/labels",
    ):
        assert (await client.get(path, headers=viewer)).status_code == 200
    outsider = team["people"]["outsider"]["headers"]
    assert (
        await client.patch(task_path, headers=outsider, json={"title": "No"})
    ).status_code == 404


async def test_label_unique_names_and_pagination(client, team):
    headers = team["people"]["owner"]["headers"]
    project_id = team["project"]["id"]
    path = f"/api/v1/projects/{project_id}/labels"
    first = (await client.post(path, headers=headers, json={"name": "Bug"})).json()
    duplicate = await client.post(path, headers=headers, json={"name": " Bug "})
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == messages.LABEL_NAME_CONFLICT
    second = (await client.post(path, headers=headers, json={"name": "Feature"})).json()
    response = await client.patch(
        f"/api/v1/labels/{second['id']}", headers=headers, json={"name": "Bug"}
    )
    assert response.status_code == 409
    page = (
        await client.get(path, headers=headers, params={"skip": 1, "limit": 1})
    ).json()
    assert page == {"items": [second], "total": 2, "skip": 1, "limit": 1}
    assert (
        await client.get(path, headers=headers, params={"limit": 0})
    ).status_code == 422
    other = (
        await client.post(
            f"/api/v1/workspaces/{team['workspace']['id']}/projects",
            headers=headers,
            json={"name": "Other"},
        )
    ).json()
    assert (
        await client.post(
            f"/api/v1/projects/{other['id']}/labels",
            headers=headers,
            json={"name": "Bug"},
        )
    ).status_code == 201
    task = await create_task(client, team)
    task_labels = f"/api/v1/tasks/{task['id']}/labels"
    for label in (first, second):
        response = await client.post(task_labels + f"/{label['id']}", headers=headers)
        assert response.status_code == 201 and response.json() == label
    page = (
        await client.get(task_labels, headers=headers, params={"skip": 1, "limit": 1})
    ).json()
    assert page == {"items": [second], "total": 2, "skip": 1, "limit": 1}


async def test_task_multivalue_filters_and_invalid_assignees(client, team):
    headers = team["people"]["owner"]["headers"]
    path = f"/api/v1/projects/{team['project']['id']}/tasks"
    first = await create_task(client, team, priority="HIGH")
    second = await create_task(client, team, priority="URGENT")
    await create_task(client, team, priority="LOW")
    assert (
        await client.patch(
            f"/api/v1/tasks/{second['id']}", headers=headers, json={"status": "DONE"}
        )
    ).status_code == 200
    response = await client.get(
        path,
        headers=headers,
        params=[
            ("status", "TODO"),
            ("status", "DONE"),
            ("priority", "HIGH"),
            ("priority", "URGENT"),
            ("limit", 1),
            ("skip", 1),
        ],
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["id"] for item in response.json()["items"]] == [second["id"]]
    for value in (0, -1):
        assert (
            await client.get(path, headers=headers, params={"assignee_id": value})
        ).status_code == 422
        assert (
            await client.post(
                path, headers=headers, json={"title": "Bad", "assignee_id": value}
            )
        ).status_code == 422
        assert (
            await client.patch(
                f"/api/v1/tasks/{first['id']}",
                headers=headers,
                json={"assignee_id": value},
            )
        ).status_code == 422
    today = datetime.now(UTC).date()
    assert (
        await client.post(
            path,
            headers=headers,
            json={"title": "Past", "due_date": str(today - timedelta(days=1))},
        )
    ).status_code == 422
    assert (
        await client.post(
            path, headers=headers, json={"title": "Today", "due_date": str(today)}
        )
    ).status_code == 201


async def test_remove_member_rolls_back_unassignment(
    client, team, session_factory, monkeypatch
):
    member_id = team["people"]["editor"]["user"]["id"]
    task = await create_task(client, team, assignee_id=member_id)
    original = WorkspaceMemberRepository.remove

    async def fail_after_delete(repo, member):
        await original(repo, member)
        raise RuntimeError("injected failure")

    monkeypatch.setattr(WorkspaceMemberRepository, "remove", fail_after_delete)
    with pytest.raises(RuntimeError, match="injected failure"):
        await client.delete(
            f"/api/v1/workspaces/{team['workspace']['id']}/members/{member_id}",
            headers=team["people"]["owner"]["headers"],
        )
    async with session_factory() as session:
        assert (await session.get(Task, task["id"])).assignee_id == member_id
        assert (
            await session.get(WorkspaceMember, (team["workspace"]["id"], member_id))
            is not None
        )


async def test_task_update_reuses_authorized_project(client, team, monkeypatch):
    task = await create_task(client, team)
    calls = []
    original = ProjectRepository.get

    async def counted(repo, project_id):
        calls.append(project_id)
        return await original(repo, project_id)

    monkeypatch.setattr(ProjectRepository, "get", counted)
    response = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=team["people"]["owner"]["headers"],
        json={"assignee_id": team["people"]["viewer"]["user"]["id"]},
    )
    assert response.status_code == 200
    assert calls == [team["project"]["id"]]


@pytest.mark.parametrize(
    "database_error,expected",
    [
        (
            "UNIQUE constraint failed: task_labels.task_id, task_labels.label_id",
            messages.LABEL_ALREADY_ATTACHED,
        ),
        ("FOREIGN KEY constraint failed", messages.RESOURCE_CHANGED),
    ],
)
async def test_attach_distinguishes_concurrent_conflicts(
    client, team, monkeypatch, database_error, expected
):
    task = await create_task(client, team)
    headers = team["people"]["owner"]["headers"]
    label = (
        await client.post(
            f"/api/v1/projects/{team['project']['id']}/labels",
            headers=headers,
            json={"name": "Bug"},
        )
    ).json()

    async def failed_attach(*args):
        raise IntegrityError("INSERT", {}, Exception(database_error))

    monkeypatch.setattr(LabelRepository, "attach", failed_attach)
    response = await client.post(
        f"/api/v1/tasks/{task['id']}/labels/{label['id']}", headers=headers
    )
    assert response.status_code == 409
    assert response.json()["detail"] == expected


async def test_label_patch_rejects_null_and_preserves_omitted_fields(client, team):
    headers = team["people"]["owner"]["headers"]
    label = (
        await client.post(
            f"/api/v1/projects/{team['project']['id']}/labels",
            headers=headers,
            json={"name": "Bug"},
        )
    ).json()
    path = f"/api/v1/labels/{label['id']}"
    for field in ("name", "color"):
        response = await client.patch(path, headers=headers, json={field: None})
        assert response.status_code == 422
        assert messages.FIELD_NOT_NULLABLE in response.json()["detail"][0]["msg"]
    assert (await client.patch(path, headers=headers, json={})).json() == label


def test_day5_openapi_documents_filters_pagination_and_errors():
    schema = app.openapi()
    listing = schema["paths"]["/api/v1/projects/{project_id}/tasks"]["get"]
    parameters = {item["name"]: item for item in listing["parameters"]}
    for name in ("status", "priority"):
        assert parameters[name]["in"] == "query"
        assert parameters[name]["schema"]["anyOf"][0]["type"] == "array"
    assert "skip" in parameters and "limit" in parameters
    for path, method in (
        ("/api/v1/tasks/{task_id}", "delete"),
        ("/api/v1/comments/{comment_id}", "delete"),
        ("/api/v1/projects/{project_id}/labels", "post"),
    ):
        operation = schema["paths"][path][method]
        assert operation["summary"]
        assert {"401", "403", "404", "409"} <= operation["responses"].keys()
        assert "400" not in operation["responses"]

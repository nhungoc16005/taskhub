import pytest_asyncio
from conftest import bearer
from sqlalchemy import select

from app.models.project import Project

WS = "/api/v1/workspaces"
PROJECTS = "/api/v1/projects"


@pytest_asyncio.fixture
async def team(client, make_user, create_workspace, invite):
    """1 workspace với owner / editor / viewer và 1 người ngoài (stranger)."""
    _, owner = await make_user("owner@x.com")
    _, editor = await make_user("editor@x.com")
    _, viewer = await make_user("viewer@x.com")
    _, stranger = await make_user("stranger@x.com")
    ws = (await create_workspace(owner)).json()
    await invite(owner, ws["id"], "editor@x.com", "EDITOR")
    await invite(owner, ws["id"], "viewer@x.com", "VIEWER")
    return {
        "ws": ws["id"],
        "owner": owner,
        "editor": editor,
        "viewer": viewer,
        "stranger": stranger,
    }


async def make_project(client, team, who="editor", name="P1"):
    return await client.post(
        f"{WS}/{team['ws']}/projects",
        headers=bearer(team[who]),
        json={"name": name, "description": "desc"},
    )


async def test_editor_creates_project(client, team):
    r = await make_project(client, team)
    assert r.status_code == 201
    data = r.json()
    assert data["workspace_id"] == team["ws"]
    assert data["status"] == "ACTIVE" and data["name"] == "P1"


async def test_viewer_cannot_create_project(client, team):
    assert (await make_project(client, team, who="viewer")).status_code == 403


async def test_stranger_cannot_create_project(client, team):
    assert (await make_project(client, team, who="stranger")).status_code == 404


async def test_viewer_can_read_project(client, team):
    p = (await make_project(client, team)).json()
    r = await client.get(f"{PROJECTS}/{p['id']}", headers=bearer(team["viewer"]))
    assert r.status_code == 200


async def test_stranger_gets_404_on_project(client, team):
    p = (await make_project(client, team)).json()
    r = await client.get(f"{PROJECTS}/{p['id']}", headers=bearer(team["stranger"]))
    assert r.status_code == 404


async def test_missing_project_returns_404(client, team):
    r = await client.get(f"{PROJECTS}/9999", headers=bearer(team["owner"]))
    assert r.status_code == 404


async def test_editor_updates_project_but_viewer_cannot(client, team):
    p = (await make_project(client, team)).json()
    ok = await client.patch(
        f"{PROJECTS}/{p['id']}", headers=bearer(team["editor"]), json={"name": "New"}
    )
    assert ok.status_code == 200 and ok.json()["name"] == "New"
    denied = await client.patch(
        f"{PROJECTS}/{p['id']}", headers=bearer(team["viewer"]), json={"name": "Hack"}
    )
    assert denied.status_code == 403


async def test_update_project_null_name_returns_422(client, team):
    p = (await make_project(client, team)).json()
    r = await client.patch(
        f"{PROJECTS}/{p['id']}", headers=bearer(team["editor"]), json={"name": None}
    )
    assert r.status_code == 422


async def test_archive_project_requires_editor(client, team):
    p = (await make_project(client, team)).json()
    denied = await client.post(
        f"{PROJECTS}/{p['id']}/archive", headers=bearer(team["viewer"])
    )
    assert denied.status_code == 403
    ok = await client.post(
        f"{PROJECTS}/{p['id']}/archive", headers=bearer(team["editor"])
    )
    assert ok.status_code == 200 and ok.json()["status"] == "ARCHIVED"


async def test_list_projects_with_status_filter_and_pagination(client, team):
    p1 = (await make_project(client, team, name="P1")).json()
    await make_project(client, team, name="P2")
    await make_project(client, team, name="P3")
    await client.post(f"{PROJECTS}/{p1['id']}/archive", headers=bearer(team["editor"]))

    url = f"{WS}/{team['ws']}/projects"
    allp = (await client.get(url, headers=bearer(team["viewer"]))).json()
    assert allp["total"] == 3

    active = (
        await client.get(
            url, headers=bearer(team["viewer"]), params={"status": "ACTIVE"}
        )
    ).json()
    assert active["total"] == 2

    page = (
        await client.get(
            url, headers=bearer(team["viewer"]), params={"skip": 1, "limit": 1}
        )
    ).json()
    assert len(page["items"]) == 1 and page["total"] == 3


async def test_only_owner_can_delete_project(client, team):
    p = (await make_project(client, team)).json()
    denied = await client.delete(
        f"{PROJECTS}/{p['id']}", headers=bearer(team["editor"])
    )
    assert denied.status_code == 403
    ok = await client.delete(f"{PROJECTS}/{p['id']}", headers=bearer(team["owner"]))
    assert ok.status_code == 204
    gone = await client.get(f"{PROJECTS}/{p['id']}", headers=bearer(team["owner"]))
    assert gone.status_code == 404


async def test_deleting_workspace_removes_its_projects(
    client, team, session_factory, create_workspace
):
    p = (await make_project(client, team)).json()
    other_ws = (await create_workspace(team["owner"], "Other workspace")).json()
    other = (
        await client.post(
            f"{WS}/{other_ws['id']}/projects",
            headers=bearer(team["owner"]),
            json={"name": "Keep me"},
        )
    ).json()
    deleted = await client.delete(f"{WS}/{team['ws']}", headers=bearer(team["owner"]))
    assert deleted.status_code == 204
    async with session_factory() as session:
        remaining = await session.scalars(
            select(Project).where(Project.workspace_id == team["ws"])
        )
        assert remaining.all() == []
        assert await session.get(Project, other["id"]) is not None
    r = await client.get(f"{PROJECTS}/{p['id']}", headers=bearer(team["owner"]))
    assert r.status_code == 404

import pytest


@pytest.mark.parametrize(
    "role,read,write",
    [
        ("owner", 200, 200),
        ("editor", 200, 403),
        ("viewer", 200, 403),
        ("outsider", 404, 404),
        ("admin", 200, 200),
    ],
)
async def test_workspace_roles(client, team, role, read, write):
    path = f"/api/v1/workspaces/{team['workspace']['id']}"
    headers = team["people"][role]["headers"]
    assert (await client.get(path, headers=headers)).status_code == read
    assert (await client.get(path + "/members", headers=headers)).status_code == read
    assert (
        await client.patch(path, json={"name": "Changed"}, headers=headers)
    ).status_code == write


@pytest.mark.parametrize(
    "role,expected",
    [
        ("owner", 204),
        ("editor", 403),
        ("viewer", 403),
        ("outsider", 404),
        ("admin", 204),
    ],
)
async def test_delete_workspace(client, team, role, expected):
    response = await client.delete(
        f"/api/v1/workspaces/{team['workspace']['id']}",
        headers=team["people"][role]["headers"],
    )
    assert response.status_code == expected
    if expected == 204:
        assert (
            await client.get(
                f"/api/v1/projects/{team['project']['id']}",
                headers=team["people"]["owner"]["headers"],
            )
        ).status_code == 404


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"email": "viewer@example.com", "role": "VIEWER"}, 409),
        ({"email": "missing@example.com", "role": "VIEWER"}, 404),
        ({"email": "outsider@example.com", "role": "OWNER"}, 422),
        ({"email": "outsider@example.com", "role": "EDITOR"}, 201),
        ({"email": "invalid", "role": "VIEWER"}, 422),
    ],
)
async def test_invitation(client, team, payload, expected):
    response = await client.post(
        f"/api/v1/workspaces/{team['workspace']['id']}/members",
        json=payload,
        headers=team["people"]["owner"]["headers"],
    )
    assert response.status_code == expected


async def test_owner_protected(client, team):
    path = f"/api/v1/workspaces/{team['workspace']['id']}/members/{team['people']['owner']['user']['id']}"
    headers = team["people"]["owner"]["headers"]
    assert (await client.delete(path, headers=headers)).status_code == 400
    assert (
        await client.patch(path, json={"role": "VIEWER"}, headers=headers)
    ).status_code == 400


async def test_workspace_pagination_and_membership(client, team):
    headers = team["people"]["owner"]["headers"]
    await client.post("/api/v1/workspaces", json={"name": "Second"}, headers=headers)
    result = (
        await client.get("/api/v1/workspaces?skip=1&limit=1", headers=headers)
    ).json()
    assert result["total"] == 2
    assert len(result["items"]) == 1
    result = (
        await client.get(
            "/api/v1/workspaces", headers=team["people"]["outsider"]["headers"]
        )
    ).json()
    assert result["total"] == 0


async def test_member_remove_and_change_role(client, team):
    path = f"/api/v1/workspaces/{team['workspace']['id']}/members/{team['people']['editor']['user']['id']}"
    headers = team["people"]["owner"]["headers"]
    response = await client.patch(path, json={"role": "VIEWER"}, headers=headers)
    assert response.status_code == 200
    editor = team["people"]["editor"]["user"]
    assert response.json() == {
        "user_id": editor["id"],
        "role": "VIEWER",
        "email": editor["email"],
        "full_name": editor["full_name"],
    }
    assert (await client.delete(path, headers=headers)).status_code == 204
    assert (await client.delete(path, headers=headers)).status_code == 404
    assert (
        await client.get(
            f"/api/v1/projects/{team['project']['id']}",
            headers=team["people"]["editor"]["headers"],
        )
    ).status_code == 404

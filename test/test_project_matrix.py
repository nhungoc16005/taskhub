import pytest


@pytest.mark.parametrize(
    "role,expected",
    [
        ("owner", 201),
        ("editor", 201),
        ("viewer", 403),
        ("outsider", 404),
        ("admin", 201),
    ],
)
async def test_project_create_roles(client, team, role, expected):
    response = await client.post(
        f"/api/v1/workspaces/{team['workspace']['id']}/projects",
        json={"name": "New"},
        headers=team["people"][role]["headers"],
    )
    assert response.status_code == expected


@pytest.mark.parametrize(
    "role,read,write,delete",
    [
        ("owner", 200, 200, 204),
        ("editor", 200, 200, 403),
        ("viewer", 200, 403, 403),
        ("outsider", 404, 404, 404),
        ("admin", 200, 200, 204),
    ],
)
async def test_project_roles(client, team, role, read, write, delete):
    path = f"/api/v1/projects/{team['project']['id']}"
    headers = team["people"][role]["headers"]
    assert (await client.get(path, headers=headers)).status_code == read
    assert (
        await client.patch(path, json={"name": "Changed"}, headers=headers)
    ).status_code == write
    assert (await client.post(path + "/archive", headers=headers)).status_code == write
    # Successful archive makes subsequent writes read-only, including deletion.
    expected_delete = 409 if write == 200 and delete == 204 else delete
    assert (await client.delete(path, headers=headers)).status_code == expected_delete


async def test_project_filter_and_pagination(client, team):
    headers = team["people"]["owner"]["headers"]
    path = f"/api/v1/workspaces/{team['workspace']['id']}/projects"
    await client.post(path, json={"name": "Second"}, headers=headers)
    await client.post(
        f"/api/v1/projects/{team['project']['id']}/archive", headers=headers
    )
    result = (
        await client.get(path + "?status=ARCHIVED&limit=1", headers=headers)
    ).json()
    assert result["total"] == 1 and result["items"][0]["status"] == "ARCHIVED"
    result = (await client.get(path + "?skip=1&limit=1", headers=headers)).json()
    assert result["total"] == 2 and len(result["items"]) == 1


async def test_project_validation(client, team):
    headers = team["people"]["owner"]["headers"]
    path = f"/api/v1/projects/{team['project']['id']}"
    for payload in ({"name": None}, {"name": " "}):
        assert (
            await client.patch(path, json=payload, headers=headers)
        ).status_code == 422
    assert (
        await client.get(
            f"/api/v1/workspaces/{team['workspace']['id']}/projects?limit=0",
            headers=headers,
        )
    ).status_code == 422
    assert (
        await client.get(
            f"/api/v1/workspaces/{team['workspace']['id']}/projects?status=INVALID",
            headers=headers,
        )
    ).status_code == 422

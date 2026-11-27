import pytest

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, NAME_MAX_LENGTH


@pytest.mark.parametrize(
    "params",
    [
        {"skip": -1},
        {"limit": 0},
        {"limit": MAX_PAGE_SIZE + 1},
        {"skip": "invalid"},
    ],
)
async def test_pagination_validation_across_endpoints(client, team, params):
    headers = team["people"]["owner"]["headers"]
    paths = [
        "/api/v1/users",
        "/api/v1/workspaces",
        f"/api/v1/workspaces/{team['workspace']['id']}/projects",
    ]
    for path in paths:
        response = await client.get(path, params=params, headers=headers)
        assert response.status_code == 422, (path, response.text)


async def test_empty_page_preserves_total_and_defaults(client, team):
    headers = team["people"]["owner"]["headers"]
    for path in ("/api/v1/users", "/api/v1/workspaces"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 200
        first = response.json()
        assert first["skip"] == 0 and first["limit"] == DEFAULT_PAGE_SIZE
        response = await client.get(
            path, params={"skip": 999, "limit": 1}, headers=headers
        )
        assert response.json() == {
            "items": [],
            "total": first["total"],
            "skip": 999,
            "limit": 1,
        }


async def test_patch_name_omission_null_and_constraints(client, team):
    headers = team["people"]["owner"]["headers"]
    paths = [
        f"/api/v1/workspaces/{team['workspace']['id']}",
        f"/api/v1/projects/{team['project']['id']}",
    ]
    for path in paths:
        original = (await client.get(path, headers=headers)).json()["name"]
        response = await client.patch(path, json={}, headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == original
        for value in (None, "  ", "x" * (NAME_MAX_LENGTH + 1)):
            response = await client.patch(path, json={"name": value}, headers=headers)
            assert response.status_code == 422
        response = await client.patch(
            path, json={"name": "  Renamed  "}, headers=headers
        )
        assert response.status_code == 200 and response.json()["name"] == "Renamed"
    response = await client.patch(paths[1], json={"description": None}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"
    assert response.json()["description"] is None

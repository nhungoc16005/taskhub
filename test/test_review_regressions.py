import pytest
from test_day5 import create_task

from app.core.constants import MAX_PAGE_SIZE


@pytest.mark.parametrize("params", [
    {"skip": -1}, {"limit": 0}, {"limit": MAX_PAGE_SIZE + 1},
    {"skip": "invalid"},
])
async def test_pagination_validation_across_endpoints(client, team, params):
    task = await create_task(client, team)
    headers = team["people"]["owner"]["headers"]
    paths = [
        "/api/v1/users", "/api/v1/workspaces",
        f"/api/v1/workspaces/{team['workspace']['id']}/projects",
        f"/api/v1/projects/{team['project']['id']}/tasks",
        f"/api/v1/tasks/{task['id']}/comments",
    ]
    for path in paths:
        response = await client.get(path, params=params, headers=headers)
        assert response.status_code == 422, (path, response.text)

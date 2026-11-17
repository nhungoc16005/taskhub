import pytest


async def create_task(client, team, role="editor", **fields):
    response = await client.post(f"/api/v1/projects/{team['project']['id']}/tasks", headers=team["people"][role]["headers"], json={"title":"Task", **fields})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("role,expected", [("owner",201),("editor",201),("viewer",403),("outsider",404),("admin",201)])
async def test_create_task_roles(client, team, role, expected):
    response = await client.post(f"/api/v1/projects/{team['project']['id']}/tasks", headers=team["people"][role]["headers"], json={"title":"Task"})
    assert response.status_code == expected
    if expected == 201:
        assert response.json()["created_by"] == team["people"][role]["user"]["id"]
        assert response.json()["status"] == "TODO"
        assert response.json()["priority"] == "MEDIUM"


@pytest.mark.parametrize("role,read,write", [("owner",200,200),("editor",200,200),("viewer",200,403),("outsider",404,404),("admin",200,200)])
async def test_task_roles(client, team, role, read, write):
    task = await create_task(client, team)
    path = f"/api/v1/tasks/{task['id']}"
    headers = team["people"][role]["headers"]
    assert (await client.get(path, headers=headers)).status_code == read
    assert (await client.patch(path, headers=headers, json={"status":"DONE","priority":"HIGH","due_date":"2026-12-01"})).status_code == write


@pytest.mark.parametrize("role,expected", [("owner",204),("editor",204),("viewer",403),("outsider",404),("admin",204)])
async def test_task_delete_roles(client, team, role, expected):
    task = await create_task(client, team)
    assert (await client.delete(f"/api/v1/tasks/{task['id']}", headers=team["people"][role]["headers"])).status_code == expected


async def test_assignee_archive_filters(client, team):
    headers = team["people"]["owner"]["headers"]
    path = f"/api/v1/projects/{team['project']['id']}/tasks"
    outsider = team["people"]["outsider"]["user"]["id"]
    assert (await client.post(path, headers=headers, json={"title":"Bad","assignee_id":outsider})).status_code == 400
    assignee = team["people"]["viewer"]["user"]["id"]
    task = await create_task(client, team, assignee_id=assignee, priority="HIGH")
    await create_task(client, team)
    result = (await client.get(path + f"?status=TODO&priority=HIGH&assignee_id={assignee}&limit=1", headers=headers)).json()
    assert result["total"] == 1 and result["items"][0]["id"] == task["id"]
    result = (await client.get(path + "?skip=1&limit=1", headers=headers)).json()
    assert result["total"] == 2 and len(result["items"]) == 1
    task_path = f"/api/v1/tasks/{task['id']}"
    assert (await client.patch(task_path, headers=headers, json={"assignee_id":outsider})).status_code == 400
    assert (await client.patch(task_path, headers=headers, json={"assignee_id":None})).json()["assignee_id"] is None
    await client.post(f"/api/v1/projects/{team['project']['id']}/archive", headers=headers)
    assert (await client.post(path, headers=headers, json={"title":"No"})).status_code == 409


@pytest.mark.parametrize("payload", [{"title":None},{"title":" "},{"priority":None},{"status":"INVALID"},{"due_date":"bad"}])
async def test_invalid_task_update(client, team, payload):
    task = await create_task(client, team)
    assert (await client.patch(f"/api/v1/tasks/{task['id']}", headers=team["people"]["owner"]["headers"], json=payload)).status_code == 422


@pytest.mark.parametrize("role,expected", [("owner",201),("editor",201),("viewer",403),("outsider",404),("admin",201)])
async def test_label_and_comment_roles(client, team, role, expected):
    task = await create_task(client, team)
    headers = team["people"][role]["headers"]
    assert (await client.post(f"/api/v1/projects/{team['project']['id']}/labels", json={"name":"Bug"}, headers=headers)).status_code == expected
    assert (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content":"Hello"}, headers=headers)).status_code == expected


async def test_labels_lifecycle_and_project_boundary(client, team):
    headers = team["people"]["owner"]["headers"]
    task = await create_task(client, team)
    path = f"/api/v1/projects/{team['project']['id']}/labels"
    assert (await client.post(path, json={"name":"Bad","color":"red"}, headers=headers)).status_code == 422
    label = (await client.post(path, json={"name":"Bug","color":"#FF0000"}, headers=headers)).json()
    attach = f"/api/v1/tasks/{task['id']}/labels/{label['id']}"
    assert (await client.post(attach, headers=headers)).status_code == 201
    assert (await client.post(attach, headers=headers)).status_code == 409
    project = (await client.post(f"/api/v1/workspaces/{team['workspace']['id']}/projects", json={"name":"Other"}, headers=headers)).json()
    other = (await client.post(f"/api/v1/projects/{project['id']}/labels", json={"name":"Other"}, headers=headers)).json()
    assert (await client.post(f"/api/v1/tasks/{task['id']}/labels/{other['id']}", headers=headers)).status_code == 404
    assert len((await client.get(path, headers=headers)).json()) == 1
    assert (await client.patch(f"/api/v1/labels/{label['id']}", json={"name":"Fixed"}, headers=headers)).status_code == 200
    assert (await client.delete(attach, headers=headers)).status_code == 204
    assert (await client.delete(attach, headers=headers)).status_code == 404
    assert (await client.delete(f"/api/v1/labels/{label['id']}", headers=headers)).status_code == 204


@pytest.mark.parametrize("role,expected", [("owner",204),("editor",204),("viewer",403),("outsider",404),("admin",204)])
async def test_comment_delete_roles(client, team, role, expected):
    task = await create_task(client, team)
    path = f"/api/v1/tasks/{task['id']}/comments"
    comment = (await client.post(path, json={"content":"Hello"}, headers=team["people"]["editor"]["headers"])).json()
    listing = (await client.get(path+"?limit=1", headers=team["people"]["viewer"]["headers"])).json()
    assert listing["total"] == 1
    assert (await client.delete(f"/api/v1/comments/{comment['id']}", headers=team["people"][role]["headers"])).status_code == expected


async def test_editor_cannot_delete_others_resources(client, team):
    task = await create_task(client, team, role="owner")
    owner = team["people"]["owner"]["headers"]
    editor = team["people"]["editor"]["headers"]
    path = f"/api/v1/tasks/{task['id']}"
    comment = (await client.post(path+"/comments", json={"content":"Owner comment"}, headers=owner)).json()
    assert (await client.delete(path, headers=editor)).status_code == 403
    assert (await client.delete(f"/api/v1/comments/{comment['id']}", headers=editor)).status_code == 403


async def test_removed_member_unassigned_and_denied(client, team):
    task = await create_task(client, team, assignee_id=team["people"]["editor"]["user"]["id"])
    owner = team["people"]["owner"]["headers"]
    await client.delete(f"/api/v1/workspaces/{team['workspace']['id']}/members/{team['people']['editor']['user']['id']}", headers=owner)
    path = f"/api/v1/tasks/{task['id']}"
    assert (await client.get(path, headers=owner)).json()["assignee_id"] is None
    assert (await client.delete(path, headers=team["people"]["editor"]["headers"])).status_code == 404


async def test_workspace_cascades_day5_resources(client, team):
    task = await create_task(client, team)
    headers = team["people"]["owner"]["headers"]
    label = (await client.post(f"/api/v1/projects/{team['project']['id']}/labels", json={"name":"Bug"}, headers=headers)).json()
    await client.post(f"/api/v1/tasks/{task['id']}/labels/{label['id']}", headers=headers)
    comment = (await client.post(f"/api/v1/tasks/{task['id']}/comments", json={"content":"Hello"}, headers=headers)).json()
    assert (await client.delete(f"/api/v1/workspaces/{team['workspace']['id']}", headers=headers)).status_code == 204
    for path in (f"/tasks/{task['id']}", f"/labels/{label['id']}", f"/comments/{comment['id']}"):
        assert (await client.delete("/api/v1"+path, headers=headers)).status_code == 404

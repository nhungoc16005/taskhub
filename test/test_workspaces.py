from conftest import bearer

WS = "/api/v1/workspaces"


async def test_create_workspace_makes_creator_owner(
    client, make_user, create_workspace
):
    user, tokens = await make_user("owner@x.com")
    r = await create_workspace(tokens, "  My WS  ")
    assert r.status_code == 201
    ws = r.json()
    assert ws["name"] == "My WS" and ws["owner_id"] == user["id"]

    members = (
        await client.get(f"{WS}/{ws['id']}/members", headers=bearer(tokens))
    ).json()
    assert members == [{
        "user_id": user["id"], "role": "OWNER",
        "email": user["email"], "full_name": user["full_name"],
    }]


async def test_list_returns_only_my_workspaces(client, make_user, create_workspace):
    _, a = await make_user("a@x.com")
    _, b = await make_user("b@x.com")
    await create_workspace(a, "A1")
    await create_workspace(a, "A2")
    await create_workspace(b, "B1")
    data = (await client.get(WS, headers=bearer(a))).json()
    assert data["total"] == 2
    assert [w["name"] for w in data["items"]] == ["A1", "A2"]


async def test_workspace_requires_auth(client):
    assert (await client.get(WS)).status_code == 401


async def test_non_member_gets_404(client, make_user, create_workspace):
    _, owner = await make_user("owner@x.com")
    _, stranger = await make_user("stranger@x.com")
    ws = (await create_workspace(owner)).json()
    assert (
        await client.get(f"{WS}/{ws['id']}", headers=bearer(stranger))
    ).status_code == 404


async def test_missing_workspace_returns_404(client, make_user):
    _, tokens = await make_user()
    assert (await client.get(f"{WS}/9999", headers=bearer(tokens))).status_code == 404


async def test_viewer_can_read_but_not_update(
    client, make_user, create_workspace, invite
):
    _, owner = await make_user("owner@x.com")
    _, viewer = await make_user("viewer@x.com")
    ws = (await create_workspace(owner)).json()
    await invite(owner, ws["id"], "viewer@x.com", "VIEWER")

    assert (
        await client.get(f"{WS}/{ws['id']}", headers=bearer(viewer))
    ).status_code == 200
    r = await client.patch(
        f"{WS}/{ws['id']}", headers=bearer(viewer), json={"name": "X"}
    )
    assert r.status_code == 403


async def test_editor_cannot_manage_members_or_delete(
    client, make_user, create_workspace, invite
):
    _, owner = await make_user("owner@x.com")
    _, editor = await make_user("editor@x.com")
    await make_user("third@x.com")
    ws = (await create_workspace(owner)).json()
    await invite(owner, ws["id"], "editor@x.com", "EDITOR")

    r = await invite(editor, ws["id"], "third@x.com")
    assert r.status_code == 403
    assert (
        await client.delete(f"{WS}/{ws['id']}", headers=bearer(editor))
    ).status_code == 403


async def test_owner_updates_workspace(client, make_user, create_workspace):
    _, owner = await make_user()
    ws = (await create_workspace(owner)).json()
    r = await client.patch(
        f"{WS}/{ws['id']}", headers=bearer(owner), json={"name": "Renamed"}
    )
    assert r.status_code == 200 and r.json()["name"] == "Renamed"


async def test_update_workspace_null_name_returns_422(
    client, make_user, create_workspace
):
    _, owner = await make_user()
    ws = (await create_workspace(owner)).json()
    r = await client.patch(
        f"{WS}/{ws['id']}", headers=bearer(owner), json={"name": None}
    )
    assert r.status_code == 422


async def test_invite_member_flow(client, make_user, create_workspace, invite):
    _, owner = await make_user("owner@x.com")
    guest, guest_tokens = await make_user("guest@x.com")
    ws = (await create_workspace(owner)).json()

    r = await invite(owner, ws["id"], "GUEST@x.com", "EDITOR")
    assert r.status_code == 201
    expected = {
        "user_id": guest["id"], "role": "EDITOR",
        "email": guest["email"], "full_name": guest["full_name"],
    }
    assert r.json() == expected
    members = await client.get(f"{WS}/{ws['id']}/members", headers=bearer(owner))
    assert members.status_code == 200
    assert expected in members.json()
    # guest giờ thấy workspace trong danh sách của mình
    assert (await client.get(WS, headers=bearer(guest_tokens))).json()["total"] == 1


async def test_invite_unknown_email_returns_404(make_user, create_workspace, invite):
    _, owner = await make_user()
    ws = (await create_workspace(owner)).json()
    assert (await invite(owner, ws["id"], "nobody@x.com")).status_code == 404


async def test_invite_twice_returns_409(make_user, create_workspace, invite):
    _, owner = await make_user("owner@x.com")
    await make_user("guest@x.com")
    ws = (await create_workspace(owner)).json()
    assert (await invite(owner, ws["id"], "guest@x.com")).status_code == 201
    assert (await invite(owner, ws["id"], "guest@x.com")).status_code == 409


async def test_cannot_invite_as_owner_role(make_user, create_workspace, invite):
    _, owner = await make_user("owner@x.com")
    await make_user("guest@x.com")
    ws = (await create_workspace(owner)).json()
    assert (await invite(owner, ws["id"], "guest@x.com", "OWNER")).status_code == 422


async def test_remove_member_and_access_revoked(
    client, make_user, create_workspace, invite
):
    _, owner = await make_user("owner@x.com")
    guest, guest_tokens = await make_user("guest@x.com")
    ws = (await create_workspace(owner)).json()
    await invite(owner, ws["id"], "guest@x.com")

    r = await client.delete(
        f"{WS}/{ws['id']}/members/{guest['id']}", headers=bearer(owner)
    )
    assert r.status_code == 204
    assert (
        await client.get(f"{WS}/{ws['id']}", headers=bearer(guest_tokens))
    ).status_code == 404


async def test_cannot_remove_owner(client, make_user, create_workspace):
    owner_user, owner = await make_user()
    ws = (await create_workspace(owner)).json()
    r = await client.delete(
        f"{WS}/{ws['id']}/members/{owner_user['id']}", headers=bearer(owner)
    )
    assert r.status_code == 400


async def test_remove_non_member_returns_404(client, make_user, create_workspace):
    _, owner = await make_user("owner@x.com")
    other, _ = await make_user("other@x.com")
    ws = (await create_workspace(owner)).json()
    r = await client.delete(
        f"{WS}/{ws['id']}/members/{other['id']}", headers=bearer(owner)
    )
    assert r.status_code == 404


async def test_global_admin_can_access_any_workspace(
    client, make_user, create_workspace
):
    _, owner = await make_user("owner@x.com")
    _, admin = await make_user("admin@x.com", admin=True)
    ws = (await create_workspace(owner)).json()
    assert (
        await client.get(f"{WS}/{ws['id']}", headers=bearer(admin))
    ).status_code == 200
    r = await client.patch(
        f"{WS}/{ws['id']}", headers=bearer(admin), json={"name": "By admin"}
    )
    assert r.status_code == 200


async def test_owner_deletes_workspace(client, make_user, create_workspace):
    _, owner = await make_user()
    ws = (await create_workspace(owner)).json()
    assert (
        await client.delete(f"{WS}/{ws['id']}", headers=bearer(owner))
    ).status_code == 204
    assert (
        await client.get(f"{WS}/{ws['id']}", headers=bearer(owner))
    ).status_code == 404

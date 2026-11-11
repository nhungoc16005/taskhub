from conftest import bearer

from app.models import Workspace

USERS = "/api/v1/users"


async def test_patch_me_updates_full_name(client, make_user):
    _, tokens = await make_user()
    r = await client.patch(
        f"{USERS}/me", headers=bearer(tokens), json={"full_name": "Bob"}
    )
    assert r.status_code == 200 and r.json()["full_name"] == "Bob"


async def test_patch_me_null_full_name_returns_422(client, make_user):
    _, tokens = await make_user()
    r = await client.patch(
        f"{USERS}/me", headers=bearer(tokens), json={"full_name": None}
    )
    assert r.status_code == 422


async def test_list_requires_auth(client):
    assert (await client.get(USERS)).status_code == 401


async def test_list_returns_items_and_total(client, make_user, register):
    _, tokens = await make_user("u0@x.com")
    await register(email="u1@x.com")
    await register(email="u2@x.com")
    data = (
        await client.get(USERS, headers=bearer(tokens), params={"skip": 1, "limit": 1})
    ).json()
    assert data["total"] == 3 and len(data["items"]) == 1
    assert data["skip"] == 1 and data["limit"] == 1


async def test_get_missing_user_returns_404(client, make_user):
    _, tokens = await make_user()
    assert (
        await client.get(f"{USERS}/9999", headers=bearer(tokens))
    ).status_code == 404


async def test_member_cannot_patch_other_user(client, make_user):
    _, member = await make_user("member@x.com")
    other, _ = await make_user("other@x.com")
    r = await client.patch(
        f"{USERS}/{other['id']}", headers=bearer(member), json={"full_name": "Hacked"}
    )
    assert r.status_code == 403


async def test_admin_can_patch_other_user(client, make_user):
    _, admin = await make_user("admin@x.com", admin=True)
    other, _ = await make_user("other@x.com")
    r = await client.patch(
        f"{USERS}/{other['id']}", headers=bearer(admin), json={"full_name": "Renamed"}
    )
    assert r.status_code == 200 and r.json()["full_name"] == "Renamed"


async def test_member_cannot_delete_admin(client, make_user):
    admin, _ = await make_user("admin@x.com", admin=True)
    _, member = await make_user("member@x.com")
    r = await client.delete(f"{USERS}/{admin['id']}", headers=bearer(member))
    assert r.status_code == 403


async def test_admin_delete_user_then_404(client, make_user):
    _, admin = await make_user("admin@x.com", admin=True)
    other, _ = await make_user("other@x.com")
    assert (
        await client.delete(f"{USERS}/{other['id']}", headers=bearer(admin))
    ).status_code == 204
    assert (
        await client.delete(f"{USERS}/{other['id']}", headers=bearer(admin))
    ).status_code == 404


async def test_delete_user_with_workspace_returns_409_not_500(
    client, make_user, session_factory
):
    _, admin = await make_user("admin@x.com", admin=True)
    owner, _ = await make_user("owner@x.com")
    async with session_factory() as s:
        s.add(Workspace(name="WS", owner_id=owner["id"]))
        await s.commit()
    r = await client.delete(f"{USERS}/{owner['id']}", headers=bearer(admin))
    assert r.status_code == 409

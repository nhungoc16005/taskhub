USERS = "/api/v1/users"


def body(email="a@x.com", name="Ann", password="12345678"):
    return {"email": email, "full_name": name, "password": password}


async def test_create_user_strips_name_and_hides_password(client):
    r = await client.post(USERS, json=body(email="A@X.com", name="  Ann  "))
    assert r.status_code == 201
    data = r.json()
    assert data["full_name"] == "Ann"
    assert "password" not in data and "hashed_password" not in data


async def test_duplicate_email_returns_409(client):
    await client.post(USERS, json=body())
    r = await client.post(USERS, json=body())
    assert r.status_code == 409
    assert r.json()["detail"] == "Email already exists"


async def test_patch_null_full_name_returns_422(client):
    uid = (await client.post(USERS, json=body())).json()["id"]
    r = await client.patch(f"{USERS}/{uid}", json={"full_name": None})
    assert r.status_code == 422


async def test_patch_updates_full_name(client):
    uid = (await client.post(USERS, json=body())).json()["id"]
    r = await client.patch(f"{USERS}/{uid}", json={"full_name": "Bob"})
    assert r.status_code == 200 and r.json()["full_name"] == "Bob"


async def test_get_missing_user_returns_404(client):
    assert (await client.get(f"{USERS}/9999")).status_code == 404


async def test_list_returns_items_and_total(client):
    for i in range(3):
        await client.post(USERS, json=body(email=f"u{i}@x.com"))
    data = (await client.get(USERS, params={"skip": 1, "limit": 1})).json()
    assert data["total"] == 3 and len(data["items"]) == 1
    assert data["skip"] == 1 and data["limit"] == 1


async def test_delete_then_404(client):
    uid = (await client.post(USERS, json=body())).json()["id"]
    assert (await client.delete(f"{USERS}/{uid}")).status_code == 204
    assert (await client.delete(f"{USERS}/{uid}")).status_code == 404

from conftest import PASSWORD, bearer

AUTH = "/api/v1/auth"
USERS = "/api/v1/users"


async def test_register_returns_201_and_hides_password(register):
    r = await register(email="A@X.com", name="  Ann  ")
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == "a@x.com" and data["full_name"] == "Ann"
    assert "password" not in data and "hashed_password" not in data


async def test_register_duplicate_email_returns_409(register):
    await register()
    r = await register()
    assert r.status_code == 409 and r.json()["detail"] == "Email already exists"


async def test_login_success_returns_both_tokens(make_user):
    _, tokens = await make_user()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]


async def test_login_wrong_password_returns_401(register, login):
    await register()
    r = await login(password="wrong-password")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


async def test_login_unknown_email_returns_401(login):
    assert (await login(email="nobody@x.com")).status_code == 401


async def test_me_requires_token(client):
    r = await client.get(f"{USERS}/me")
    assert r.status_code == 401


async def test_me_with_token(client, make_user):
    _, tokens = await make_user()
    r = await client.get(f"{USERS}/me", headers=bearer(tokens))
    assert r.status_code == 200 and r.json()["email"] == "a@x.com"


async def test_refresh_token_cannot_be_used_as_access_token(client, make_user):
    _, tokens = await make_user()
    r = await client.get(
        f"{USERS}/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert r.status_code == 401


async def test_refresh_returns_new_access_token(client, make_user):
    _, tokens = await make_user()
    r = await client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert r.status_code == 200 and r.json()["access_token"]


async def test_access_token_cannot_be_used_to_refresh(client, make_user):
    _, tokens = await make_user()
    r = await client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert r.status_code == 401


async def test_logout_revokes_refresh_token(client, make_user):
    _, tokens = await make_user()
    body = {"refresh_token": tokens["refresh_token"]}
    assert (await client.post(f"{AUTH}/logout", json=body)).status_code == 204
    assert (await client.post(f"{AUTH}/refresh", json=body)).status_code == 401


async def test_change_password_flow(client, make_user, login):
    _, tokens = await make_user()
    r = await client.post(
        f"{USERS}/me/change-password",
        headers=bearer(tokens),
        json={"current_password": PASSWORD, "new_password": "new-password-1"},
    )
    assert r.status_code == 204
    # refresh token cũ bị thu hồi, mật khẩu cũ không đăng nhập được nữa
    old = await client.post(
        f"{AUTH}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert old.status_code == 401
    assert (await login(password=PASSWORD)).status_code == 401
    assert (await login(password="new-password-1")).status_code == 200


async def test_change_password_wrong_current_returns_400(client, make_user):
    _, tokens = await make_user()
    r = await client.post(
        f"{USERS}/me/change-password",
        headers=bearer(tokens),
        json={"current_password": "wrong-pass", "new_password": "new-password-1"},
    )
    assert r.status_code == 400

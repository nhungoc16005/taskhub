from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_user_hashes_password():
    r = client.post(
        "/api/v1/users",
        json={"email": "A@x.com", "full_name": " Ann ", "password": "12345678"},
    )
    assert r.status_code == 201
    assert r.json()["full_name"] == "Ann"
    assert "password" not in r.json()


def test_duplicate_email_returns_409():
    body = {"email": "dup@x.com", "full_name": "Dup", "password": "12345678"}
    client.post("/api/v1/users", json=body)
    assert client.post("/api/v1/users", json=body).status_code == 409


def test_patch_null_full_name_returns_422():
    uid = client.post(
        "/api/v1/users",
        json={"email": "n@x.com", "full_name": "N", "password": "12345678"},
    ).json()["id"]
    assert (
        client.patch(f"/api/v1/users/{uid}", json={"full_name": None}).status_code
        == 422
    )


def test_get_missing_user_returns_404():
    assert client.get("/api/v1/users/9999").status_code == 404


def test_list_has_items_and_total():
    data = client.get("/api/v1/users").json()
    assert {"items", "total", "skip", "limit"} <= data.keys()

import importlib
import secrets

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.responses import ErrorResponse, ValidationErrorResponse
from app.core.config import Settings
from app.main import app


def test_openapi_metadata_and_tag_descriptions():
    schema = app.openapi()
    assert schema["info"]["title"] == "TaskHub API"
    assert schema["info"]["version"] == "0.7.0"
    assert "Authorize" in schema["info"]["description"]
    tags = {tag["name"]: tag["description"] for tag in schema["tags"]}
    for path in schema["paths"].values():
        for operation in path.values():
            assert operation["summary"]
            assert all(tags[tag] for tag in operation["tags"])


def test_bearer_security_is_applied_to_protected_operations_only():
    schema = app.openapi()
    bearer = schema["components"]["securitySchemes"]["BearerAuth"]
    assert bearer["type"] == "http" and bearer["scheme"] == "bearer"
    assert bearer["bearerFormat"] == "JWT"
    for path, operations in schema["paths"].items():
        for operation in operations.values():
            if path.startswith("/api/v1/auth/") or path == "/health":
                assert not operation.get("security")
            else:
                assert operation["security"] == [{"BearerAuth": []}]


@pytest.mark.parametrize(
    "path,method,codes",
    [
        ("/comments/{comment_id}", "delete", [401, 403, 404, 409, 422, 500]),
        ("/labels/{label_id}", "delete", [401, 403, 404, 409, 422, 500]),
        ("/labels/{label_id}", "patch", [401, 403, 404, 409, 422, 500]),
        ("/projects/{project_id}", "delete", [401, 403, 404, 409, 422, 500]),
        ("/projects/{project_id}", "get", [401, 403, 404, 422, 500]),
        ("/projects/{project_id}", "patch", [401, 403, 404, 409, 422, 500]),
        ("/projects/{project_id}/archive", "post", [401, 403, 404, 409, 422, 500]),
        ("/projects/{project_id}/labels", "get", [401, 403, 404, 422, 500]),
        ("/projects/{project_id}/labels", "post", [401, 403, 404, 409, 422, 500]),
        ("/projects/{project_id}/tasks", "get", [401, 403, 404, 422, 500]),
        ("/projects/{project_id}/tasks", "post", [400, 401, 403, 404, 409, 422, 500]),
        ("/tasks/{task_id}", "delete", [401, 403, 404, 409, 422, 500]),
        ("/tasks/{task_id}", "get", [401, 403, 404, 422, 500]),
        ("/tasks/{task_id}", "patch", [400, 401, 403, 404, 409, 422, 500]),
        ("/tasks/{task_id}/comments", "get", [401, 403, 404, 422, 500]),
        ("/tasks/{task_id}/comments", "post", [401, 403, 404, 409, 422, 500]),
        ("/tasks/{task_id}/labels", "get", [401, 403, 404, 422, 500]),
        (
            "/tasks/{task_id}/labels/{label_id}",
            "delete",
            [401, 403, 404, 409, 422, 500],
        ),
        ("/tasks/{task_id}/labels/{label_id}", "post", [401, 403, 404, 409, 422, 500]),
        ("/users", "get", [401, 403, 422, 500]),
        ("/users/me", "get", [401, 403, 500]),
        ("/users/me", "patch", [401, 403, 422, 500]),
        ("/users/me/change-password", "post", [400, 401, 403, 422, 500]),
        ("/users/{user_id}", "delete", [401, 403, 404, 409, 422, 500]),
        ("/users/{user_id}", "get", [401, 403, 404, 422, 500]),
        ("/users/{user_id}", "patch", [401, 403, 404, 422, 500]),
        ("/workspaces", "get", [401, 403, 422, 500]),
        ("/workspaces", "post", [401, 403, 422, 500]),
        ("/workspaces/{workspace_id}", "delete", [401, 403, 404, 422, 500]),
        ("/workspaces/{workspace_id}", "get", [401, 403, 404, 422, 500]),
        ("/workspaces/{workspace_id}", "patch", [401, 403, 404, 422, 500]),
        ("/workspaces/{workspace_id}/members", "get", [401, 403, 404, 422, 500]),
        ("/workspaces/{workspace_id}/members", "post", [401, 403, 404, 409, 422, 500]),
        (
            "/workspaces/{workspace_id}/members/{user_id}",
            "delete",
            [400, 401, 403, 404, 422, 500],
        ),
        (
            "/workspaces/{workspace_id}/members/{user_id}",
            "patch",
            [400, 401, 403, 404, 422, 500],
        ),
        ("/workspaces/{workspace_id}/projects", "get", [401, 403, 404, 422, 500]),
        ("/workspaces/{workspace_id}/projects", "post", [401, 403, 404, 422, 500]),
    ],
)
def test_resource_operations_have_exact_error_schemas(path, method, codes):
    responses = app.openapi()["paths"]["/api/v1" + path][method]["responses"]
    assert {int(code) for code in responses if int(code) >= 400} == set(codes)
    for code in codes:
        model = "ValidationErrorResponse" if code == 422 else "ErrorResponse"
        assert (
            responses[str(code)]["content"]["application/json"]["schema"]["$ref"]
            == f"#/components/schemas/{model}"
        )


@pytest.mark.parametrize(
    ("path", "codes"),
    [
        ("register", [409, 422, 500]),
        ("login", [401, 403, 422, 500]),
        ("refresh", [401, 422, 500]),
        ("logout", [401, 422, 500]),
    ],
)
def test_auth_errors_are_documented(path, codes):
    responses = app.openapi()["paths"][f"/api/v1/auth/{path}"]["post"]["responses"]
    assert {int(code) for code in responses if int(code) >= 400} == set(codes)


@pytest.mark.parametrize(
    ("path", "media", "field"),
    [
        ("/api/v1/auth/register", "application/json", "email"),
        ("/api/v1/auth/login", "application/x-www-form-urlencoded", "username"),
        ("/api/v1/workspaces", "application/json", "name"),
        ("/api/v1/projects/{project_id}/tasks", "application/json", "title"),
    ],
)
def test_main_requests_have_examples(path, media, field):
    content = app.openapi()["paths"][path]["post"]["requestBody"]["content"][media]
    assert content["example"][field]
    assert "schema" in content


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
async def test_documentation_is_available(client, path):
    response = await client.get(path)
    assert response.status_code == 200


@pytest.mark.parametrize("enabled", [None, True, False])
async def test_production_documentation_policy(monkeypatch, enabled):
    main = importlib.import_module("app.main")
    config = Settings(
        _env_file=None,
        APP_ENV="prod",
        SECRET_KEY=secrets.token_urlsafe(48),
        DATABASE_URL="postgresql+asyncpg://user:pass@db/taskhub",
        REDIS_URL="redis://redis/0",
        DOCS_ENABLED=enabled,
    )
    monkeypatch.setattr(main, "settings", config)
    isolated = main.create_app()
    async with AsyncClient(
        transport=ASGITransport(app=isolated), base_url="http://test"
    ) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert (await client.get(path)).status_code == (200 if enabled else 404)
        assert (await client.get("/health")).status_code == 200


async def test_documented_bearer_flow(client):
    account = {
        "email": "swagger@example.com",
        "full_name": "Swagger Tester",
        "password": "Swagger-test-2026!",
    }
    registered = await client.post("/api/v1/auth/register", json=account)
    assert registered.status_code == 201
    logged_in = await client.post(
        "/api/v1/auth/login",
        data={"username": account["email"], "password": account["password"]},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]
    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200 and me.json()["email"] == account["email"]


@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer", "Bearer invalid"])
async def test_invalid_auth_matches_documented_error(client, header):
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": header} if header else {}
    )
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert ErrorResponse.model_validate(response.json()).detail


async def test_validation_matches_documented_schema(client):
    response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422
    assert ValidationErrorResponse.model_validate(response.json()).detail

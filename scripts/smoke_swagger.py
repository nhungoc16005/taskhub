import argparse
import json
from urllib.parse import urlsplit
from uuid import uuid4

from playwright.sync_api import expect, sync_playwright


def run(base_url: str, channel: str | None) -> None:
    if urlsplit(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use a local disposable Docker stack for this smoke test")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel, headless=True)
        try:
            page = browser.new_page()
            page.goto(f"{base_url}/docs")
            page.locator(".opblock").first.wait_for()
            account = {
                "email": f"swagger-{uuid4().hex[:12]}@example.com",
                "full_name": "Swagger Smoke Tester",
                "password": "Swagger-smoke-2026!",
            }
            register = page.locator(
                "#operations-auth-register_api_v1_auth_register_post"
            )
            register.locator(".opblock-summary").click()
            register.get_by_role("button", name="Try it out").click()
            register.locator("textarea").fill(json.dumps(account))
            with page.expect_response(
                lambda response: (
                    response.url.endswith("/api/v1/auth/register")
                    and response.request.method == "POST"
                )
            ) as registered:
                register.get_by_role("button", name="Execute", exact=True).click()
            assert registered.value.status == 201, registered.value.status
            login = page.locator("#operations-auth-login_api_v1_auth_login_post")
            login.locator(".opblock-summary").click()
            login.get_by_role("button", name="Try it out").click()
            login.locator('input[placeholder="username"]').fill(account["email"])
            login.locator('input[placeholder="password"]').fill(account["password"])
            with page.expect_response(
                lambda response: (
                    response.url.endswith("/api/v1/auth/login")
                    and response.request.method == "POST"
                )
            ) as logged_in:
                login.get_by_role("button", name="Execute", exact=True).click()
            assert logged_in.value.status == 200, logged_in.value.status
            token = logged_in.value.json()["access_token"]
            page.get_by_role("button", name="Authorize", exact=True).first.click()
            modal = page.locator(".dialog-ux")
            modal.locator("input").fill(token)
            modal.get_by_role("button", name="Apply credentials", exact=True).click()
            modal.get_by_role("button", name="Close", exact=True).click()
            me = page.locator("#operations-users-read_me_api_v1_users_me_get")
            me.locator(".opblock-summary").click()
            me.get_by_role("button", name="Try it out").click()
            with page.expect_response(
                lambda response: response.url.endswith("/api/v1/users/me")
            ) as profile:
                me.get_by_role("button", name="Execute", exact=True).click()
            assert profile.value.status == 200, profile.value.status
            assert profile.value.json()["email"] == account["email"]
            page.goto(f"{base_url}/redoc")
            expect(
                page.get_by_role("heading", name="TaskHub API", exact=False)
            ).to_be_visible(timeout=30000)
            health = page.request.get(f"{base_url}/health")
            assert health.status == 200 and health.json() == {"status": "ok"}
            print(
                "PASS: /health, Swagger register 201, login 200, Authorize + /users/me 200, ReDoc rendered"
            )
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Exercise Swagger UI against a local Docker stack"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--channel", default=None)
    args = parser.parse_args()
    run(args.base_url.rstrip("/"), args.channel)

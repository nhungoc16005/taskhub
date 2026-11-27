import logging
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import update
from test_day6 import email_delivery, owner_headers, task_list  # noqa: F401

from app.models.user import User
from app.services.email_service import EmailService


@pytest.mark.parametrize(
    "request_id", ["abc status=200 path=/x", "a=b", "has space", "x" * 129, ""]
)
async def test_request_id_rejects_log_field_injection(client, caplog, request_id):
    with caplog.at_level(logging.INFO):
        response = await client.get("/health", headers={"X-Request-ID": request_id})
    actual = response.headers["X-Request-ID"]
    assert str(UUID(actual)) == actual
    assert "abc status=200 path=/x" not in caplog.text


async def test_assignment_logs_only_identifiers(caplog):
    with caplog.at_level(logging.INFO):
        await EmailService().deliver_assignment(123, 456)
    assert caplog.records[-1].getMessage() == "Assignment email user_id=123 task_id=456"


async def test_delivery_failure_does_not_log_provider_pii(caplog):
    service = EmailService()
    service.send_assignment = AsyncMock(
        side_effect=RuntimeError("private@example.com private title")
    )
    with caplog.at_level(logging.ERROR):
        await service.deliver_assignment(123, 456)
    assert "private" not in caplog.text


@pytest.mark.parametrize("operation", ["create", "update"])
async def test_inactive_assignee_receives_no_email(
    client,
    team,
    session_factory,
    email_delivery,  # noqa: F811
    operation,  # noqa: F811
):
    user_id = team["people"]["viewer"]["user"]["id"]
    async with session_factory() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
        await session.commit()
    path, headers = task_list(team), owner_headers(team)
    if operation == "create":
        response = await client.post(
            path,
            headers=headers,
            json={"title": "Private title", "assignee_id": user_id},
        )
        assert response.status_code == 201
    else:
        created = await client.post(
            path, headers=headers, json={"title": "Private title"}
        )
        response = await client.patch(
            f"/api/v1/tasks/{created.json()['id']}",
            headers=headers,
            json={"assignee_id": user_id},
        )
        assert response.status_code == 200
    email_delivery.assert_not_awaited()

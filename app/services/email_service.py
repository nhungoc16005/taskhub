import logging
from collections.abc import Callable
from typing import Protocol

from app.core import messages

logger = logging.getLogger(__name__)


class BackgroundQueue(Protocol):
    def add_task(self, func: Callable, *args, **kwargs) -> None: ...


class EmailService:
    async def send_assignment(self, recipient: str, task_id: int, title: str) -> None:
        """Development delivery: log only, no external email provider."""
        logger.info(
            "email recipient=%s subject=%s task_id=%s title=%s",
            recipient,
            messages.ASSIGNMENT_EMAIL_SUBJECT,
            task_id,
            title,
        )

    async def deliver_assignment(
        self, recipient: str, task_id: int, title: str
    ) -> None:
        try:
            await self.send_assignment(recipient, task_id, title)
        except Exception:
            logger.exception(messages.EMAIL_DELIVERY_FAILED, task_id)

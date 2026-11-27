import logging
from collections.abc import Callable
from typing import Protocol

from app.core import messages

logger = logging.getLogger(__name__)


class BackgroundQueue(Protocol):
    def add_task(self, func: Callable, *args, **kwargs) -> None: ...


class EmailService:
    async def send_assignment(self, user_id: int, task_id: int) -> None:
        """Development delivery only. A real provider must use async I/O."""
        logger.info(
            messages.ASSIGNMENT_EMAIL_LOG,
            user_id,
            task_id,
        )

    async def deliver_assignment(self, user_id: int, task_id: int) -> None:
        try:
            await self.send_assignment(user_id, task_id)
        except Exception:  # noqa: BLE001 - delivery must never fail a committed request
            logger.error(messages.EMAIL_DELIVERY_FAILED, task_id)

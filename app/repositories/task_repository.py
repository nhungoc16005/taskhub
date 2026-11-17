from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession):
        super().__init__(Task, session)

    @staticmethod
    def _conditions(
        project_id: int,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
    ) -> list:
        conditions = [Task.project_id == project_id]
        if status is not None:
            conditions.append(Task.status == status)
        if priority is not None:
            conditions.append(Task.priority == priority)
        if assignee_id is not None:
            conditions.append(Task.assignee_id == assignee_id)
        return conditions

    async def list_by_project(
        self,
        project_id: int,
        skip: int,
        limit: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
    ) -> Sequence[Task]:
        stmt = (
            select(Task)
            .where(*self._conditions(project_id, status, priority, assignee_id))
            .order_by(Task.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_project(
        self,
        project_id: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(*self._conditions(project_id, status, priority, assignee_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

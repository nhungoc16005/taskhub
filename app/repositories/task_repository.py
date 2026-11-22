from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.common import Pagination
from app.core.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.transactional import TransactionalRepository


class TaskRepository(TransactionalRepository[Task]):
    def __init__(self, session: AsyncSession):
        super().__init__(Task, session)

    @staticmethod
    def _conditions(
        project_id: int,
        status: list[TaskStatus] | None,
        priority: list[TaskPriority] | None,
        assignee_id: int | None,
    ) -> list:
        conditions = [Task.project_id == project_id]
        if status is not None:
            conditions.append(Task.status.in_(status))
        if priority is not None:
            conditions.append(Task.priority.in_(priority))
        if assignee_id is not None:
            conditions.append(Task.assignee_id == assignee_id)
        return conditions

    async def list_by_project(
        self,
        project_id: int,
        pagination: Pagination,
        status: list[TaskStatus] | None = None,
        priority: list[TaskPriority] | None = None,
        assignee_id: int | None = None,
    ) -> Sequence[Task]:
        stmt = (
            select(Task)
            .where(*self._conditions(project_id, status, priority, assignee_id))
            .order_by(Task.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_project(
        self,
        project_id: int,
        status: list[TaskStatus] | None = None,
        priority: list[TaskPriority] | None = None,
        assignee_id: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Task)
            .where(*self._conditions(project_id, status, priority, assignee_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def unassign_in_workspace(self, workspace_id: int, user_id: int) -> None:
        await self.session.execute(
            update(Task).where(
                Task.project_id.in_(select(Project.id).where(Project.workspace_id == workspace_id)),
                Task.assignee_id == user_id,
            ).values(assignee_id=None)
        )
        await self.session.flush()

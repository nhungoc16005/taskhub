from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectStatus
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession):
        super().__init__(Project, session)

    async def list_by_workspace(
        self,
        workspace_id: int,
        skip: int,
        limit: int,
        status: ProjectStatus | None = None,
    ) -> Sequence[Project]:
        stmt = select(Project).where(Project.workspace_id == workspace_id)
        if status is not None:
            stmt = stmt.where(Project.status == status)
        stmt = stmt.order_by(Project.id).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_workspace(
        self, workspace_id: int, status: ProjectStatus | None = None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace_id)
        )
        if status is not None:
            stmt = stmt.where(Project.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

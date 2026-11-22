from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession):
        super().__init__(Workspace, session)

    async def create_with_owner(self, name: str, owner_id: int) -> Workspace:
        """Tạo workspace và thêm owner vào workspace_members trong 1 transaction."""
        workspace = Workspace(name=name, owner_id=owner_id)
        workspace.members.append(
            WorkspaceMember(user_id=owner_id, role=WorkspaceRole.OWNER)
        )
        self.session.add(workspace)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def list_for_user(
        self, user_id: int, skip: int, limit: int
    ) -> Sequence[Workspace]:
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_for_user(self, user_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

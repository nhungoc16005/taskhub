from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import WorkspaceMember, WorkspaceRole


class WorkspaceMemberRepository:
    """workspace_members có khóa chính kép (workspace_id, user_id) nên không dùng BaseRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return await self.session.get(WorkspaceMember, (workspace_id, user_id))

    async def list_by_workspace(self, workspace_id: int) -> Sequence[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(
        self, workspace_id: int, user_id: int, role: WorkspaceRole
    ) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.session.add(member)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(member)
        return member

    async def remove(self, member: WorkspaceMember) -> None:
        await self.session.delete(member)
        await self.session.commit()

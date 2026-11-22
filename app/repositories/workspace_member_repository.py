from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.models.project import Project
from app.models.task import Task


class WorkspaceMemberRepository:
    """workspace_members có khóa chính kép (workspace_id, user_id) nên không dùng BaseRepository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return await self.session.get(WorkspaceMember, (workspace_id, user_id))

    async def list_by_workspace(self, workspace_id: int) -> Sequence[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
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
        await self.session.refresh(member, attribute_names=["role", "user"])
        return member

    async def remove(self, member: WorkspaceMember) -> None:
        await self.session.execute(
            update(Task).where(
                Task.project_id.in_(
                    select(Project.id).where(Project.workspace_id == member.workspace_id)
                ),
                Task.assignee_id == member.user_id,
            ).values(assignee_id=None)
        )
        await self.session.delete(member)
        await self.session.commit()

    async def update_role(
        self, member: WorkspaceMember, role: WorkspaceRole
    ) -> WorkspaceMember:
        member.role = role
        await self.session.commit()
        await self.session.refresh(member, attribute_names=["role", "user"])
        return member

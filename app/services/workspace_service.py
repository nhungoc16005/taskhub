from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    AlreadyMemberError,
    CannotRemoveOwnerError,
    CannotDemoteOwnerError,
    ForbiddenError,
    MemberNotFoundError,
    UserNotFoundError,
    WorkspaceNotFoundError,
)
from app.core.permissions import has_workspace_role
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import Page, Pagination
from app.schemas.workspace import MemberInvite, MemberUpdate, WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def __init__(
        self,
        repo: WorkspaceRepository,
        member_repo: WorkspaceMemberRepository,
        user_repo: UserRepository,
    ):
        self.repo = repo
        self.member_repo = member_repo
        self.user_repo = user_repo

    async def get_with_role(
        self, user: User, workspace_id: int, required: WorkspaceRole
    ) -> Workspace:
        """Trả workspace nếu user có ít nhất quyền `required`.

        - Không tồn tại hoặc user không phải thành viên -> 404 (không lộ sự tồn tại)
        - Là thành viên nhưng thiếu quyền -> 403
        - ADMIN toàn hệ thống được coi như OWNER của mọi workspace
        """
        workspace = await self.repo.get(workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundError()
        if user.role == UserRole.ADMIN:
            return workspace

        member = await self.member_repo.get(workspace_id, user.id)
        if member is None:
            raise WorkspaceNotFoundError()
        if not has_workspace_role(member.role, required):
            raise ForbiddenError()
        return workspace

    async def create(self, user: User, data: WorkspaceCreate) -> Workspace:
        return await self.repo.create_with_owner(data.name, user.id)

    async def list_for_user(
        self, user: User, pagination: Pagination
    ) -> Page[Workspace]:
        return pagination.page(
            items=await self.repo.list_for_user(
                user.id, pagination.skip, pagination.limit
            ),
            total=await self.repo.count_for_user(user.id),
        )

    async def update(self, workspace: Workspace, data: WorkspaceUpdate) -> Workspace:
        return await self.repo.update(workspace, data.model_dump(exclude_unset=True))

    async def delete(self, workspace: Workspace) -> None:
        await self.repo.delete(workspace)

    async def list_members(self, workspace: Workspace):
        return await self.member_repo.list_by_workspace(workspace.id)

    async def add_member(
        self, workspace: Workspace, data: MemberInvite
    ) -> WorkspaceMember:
        invited = await self.user_repo.get_by_email(data.email.lower())
        if invited is None:
            raise UserNotFoundError()
        if await self.member_repo.get(workspace.id, invited.id):
            raise AlreadyMemberError()
        try:
            return await self.member_repo.add(workspace.id, invited.id, data.role)
        except IntegrityError:
            raise AlreadyMemberError()

    async def remove_member(self, workspace: Workspace, user_id: int) -> None:
        if user_id == workspace.owner_id:
            raise CannotRemoveOwnerError()
        member = await self.member_repo.get(workspace.id, user_id)
        if member is None:
            raise MemberNotFoundError()
        await self.member_repo.remove(member)

    async def update_member(
        self, workspace: Workspace, user_id: int, data: MemberUpdate
    ) -> WorkspaceMember:
        if user_id == workspace.owner_id:
            raise CannotDemoteOwnerError()
        member = await self.member_repo.get(workspace.id, user_id)
        if member is None:
            raise MemberNotFoundError()
        try:
            member = await self.member_repo.update_role(member, data.role)
            await self.member_repo.session.commit()
            return member
        except Exception:
            await self.member_repo.session.rollback()
            raise

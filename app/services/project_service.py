from app.core.enums import ProjectStatus
from app.core.exceptions import (
    ProjectArchivedError,
    ProjectNotFoundError,
    WorkspaceNotFoundError,
)
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import Page, Pagination
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.resource_policy import resolve_nested_resource
from app.services.updates import update_from_schema
from app.services.workspace_service import WorkspaceService


class ProjectService:
    def __init__(self, repo: ProjectRepository, workspace_service: WorkspaceService):
        self.repo = repo
        self.workspace_service = workspace_service

    async def get_with_role(
        self,
        user: User,
        project_id: int,
        required: WorkspaceRole,
        *,
        writable: bool = False,
    ) -> Project:
        """Quyền trên project = quyền của user trong workspace chứa project đó."""
        project, _ = await resolve_nested_resource(
            self.repo.get,
            project_id,
            ProjectNotFoundError,
            lambda p: self.workspace_service.get_with_role(
                user, p.workspace_id, required
            ),
            WorkspaceNotFoundError,
        )
        if writable:
            self.ensure_writable(project)
        return project

    @staticmethod
    def ensure_writable(project: Project) -> None:
        """Kiểm tra dự án có ở trạng thái cho phép chỉnh sửa nội dung hay không."""
        if project.status == ProjectStatus.ARCHIVED:
            raise ProjectArchivedError()

    async def require_owner(self, user: User, project: Project) -> None:
        """Kiểm tra quyền OWNER trên workspace chứa dự án."""
        await self.workspace_service.get_with_role(
            user, project.workspace_id, WorkspaceRole.OWNER
        )

    async def create(self, workspace: Workspace, data: ProjectCreate) -> Project:
        return await self.repo.create(
            {**data.model_dump(), "workspace_id": workspace.id}
        )

    async def list_by_workspace(
        self,
        workspace: Workspace,
        pagination: Pagination,
        status: ProjectStatus | None,
    ) -> Page[Project]:
        return pagination.page(
            items=await self.repo.list_by_workspace(
                workspace.id, pagination.skip, pagination.limit, status
            ),
            total=await self.repo.count_by_workspace(workspace.id, status),
        )

    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        return await update_from_schema(self.repo, project, data)

    async def archive(self, project: Project) -> Project:
        return await self.repo.update(project, {"status": ProjectStatus.ARCHIVED})

    async def delete(self, project: Project) -> None:
        await self.repo.delete(project)

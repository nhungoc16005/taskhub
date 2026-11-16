from app.core.exceptions import ProjectNotFoundError, WorkspaceNotFoundError
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceRole
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.workspace_service import WorkspaceService


class ProjectService:
    def __init__(self, repo: ProjectRepository, workspace_service: WorkspaceService):
        self.repo = repo
        self.workspace_service = workspace_service

    async def get_with_role(
        self, user: User, project_id: int, required: WorkspaceRole
    ) -> Project:
        """Quyền trên project = quyền của user trong workspace chứa project đó."""
        project = await self.repo.get(project_id)
        if project is None:
            raise ProjectNotFoundError()
        try:
            await self.workspace_service.get_with_role(
                user, project.workspace_id, required
            )
        except WorkspaceNotFoundError:
            raise ProjectNotFoundError()
        return project

    async def create(self, workspace: Workspace, data: ProjectCreate) -> Project:
        return await self.repo.create(
            {**data.model_dump(), "workspace_id": workspace.id}
        )

    async def list_by_workspace(
        self,
        workspace: Workspace,
        skip: int,
        limit: int,
        status: ProjectStatus | None,
    ) -> dict:
        return {
            "items": await self.repo.list_by_workspace(
                workspace.id, skip, limit, status
            ),
            "total": await self.repo.count_by_workspace(workspace.id, status),
            "skip": skip,
            "limit": limit,
        }

    async def update(self, project: Project, data: ProjectUpdate) -> Project:
        return await self.repo.update(project, data.model_dump(exclude_unset=True))

    async def archive(self, project: Project) -> Project:
        return await self.repo.update(project, {"status": ProjectStatus.ARCHIVED})

    async def delete(self, project: Project) -> None:
        await self.repo.delete(project)

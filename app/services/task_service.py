from app.core.exceptions import (
    AssigneeNotMemberError,
    ProjectArchivedError,
    ProjectNotFoundError,
    TaskNotFoundError,
)
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_service import ProjectService
from app.services.workspace_service import WorkspaceService


class TaskService:
    def __init__(
        self,
        repo: TaskRepository,
        project_service: ProjectService,
        workspace_service: WorkspaceService,
    ):
        self.repo = repo
        self.project_service = project_service
        self.workspace_service = workspace_service

    async def get_with_role(
        self, user: User, task_id: int, required: WorkspaceRole
    ) -> Task:
        """Quyền trên task = quyền của user trong workspace chứa project của task."""
        task = await self.repo.get(task_id)
        if task is None:
            raise TaskNotFoundError()
        try:
            await self.project_service.get_with_role(user, task.project_id, required)
        except ProjectNotFoundError:
            raise TaskNotFoundError()
        return task

    async def require_owner(self, user: User, task: Task) -> None:
        """Yêu cầu user là OWNER (hoặc ADMIN) của workspace chứa task."""
        project = await self.project_service.repo.get(task.project_id)
        await self.workspace_service.get_with_role(
            user, project.workspace_id, WorkspaceRole.OWNER
        )

    async def _check_assignee(self, workspace_id: int, assignee_id: int) -> None:
        member = await self.workspace_service.member_repo.get(workspace_id, assignee_id)
        if member is None:
            raise AssigneeNotMemberError()

    async def create(self, user: User, project: Project, data: TaskCreate) -> Task:
        if project.status == ProjectStatus.ARCHIVED:
            raise ProjectArchivedError()
        if data.assignee_id is not None:
            await self._check_assignee(project.workspace_id, data.assignee_id)
        return await self.repo.create(
            {**data.model_dump(), "project_id": project.id, "created_by": user.id}
        )

    async def list_by_project(
        self,
        project: Project,
        skip: int,
        limit: int,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
    ) -> dict:
        return {
            "items": await self.repo.list_by_project(
                project.id, skip, limit, status, priority, assignee_id
            ),
            "total": await self.repo.count_by_project(
                project.id, status, priority, assignee_id
            ),
            "skip": skip,
            "limit": limit,
        }

    async def update(self, task: Task, data: TaskUpdate) -> Task:
        changes = data.model_dump(exclude_unset=True)
        if changes.get("assignee_id") is not None:
            project = await self.project_service.repo.get(task.project_id)
            await self._check_assignee(project.workspace_id, changes["assignee_id"])
        return await self.repo.update(task, changes)

    async def delete(self, user: User, task: Task) -> None:
        """Người tạo task hoặc OWNER/ADMIN mới được xóa."""
        if task.created_by != user.id:
            await self.require_owner(user, task)
        await self.repo.delete(task)

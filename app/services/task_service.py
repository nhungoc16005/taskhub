import logging

from pydantic import ValidationError

from app.core import messages
from app.core.cache import TaskCache
from app.core.enums import TaskPriority, TaskStatus
from app.core.exceptions import (
    AssigneeNotMemberError,
    TaskNotFoundError,
)
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.task_repository import TaskRepository
from app.schemas.common import Page, Pagination
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.email_service import BackgroundQueue, EmailService
from app.services.project_service import ProjectService
from app.services.resource_policy import AuthorizedResource, ProjectResourcePolicy
from app.services.transaction import transaction
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        repo: TaskRepository,
        project_service: ProjectService,
        workspace_service: WorkspaceService,
        cache: TaskCache,
        users: UserService,
        email: EmailService,
    ):
        self.repo = repo
        self.project_service = project_service
        self.workspace_service = workspace_service
        self.policy = ProjectResourcePolicy(project_service)
        self.cache = cache
        self.users = users
        self.email = email

    async def get_with_role(
        self,
        user: User,
        task_id: int,
        required: WorkspaceRole,
        *,
        writable: bool = False,
    ) -> AuthorizedResource[Task]:
        return await self.policy.load(
            self.repo.get, task_id, user, required, TaskNotFoundError, writable=writable
        )

    async def _check_assignee(self, workspace_id: int, assignee_id: int) -> None:
        if not await self.workspace_service.is_member(workspace_id, assignee_id):
            raise AssigneeNotMemberError()

    async def _recipient(
        self, user: User, new: int | None, old: int | None
    ) -> str | None:
        if new is None or new == old or new == user.id:
            return None
        return (await self.users.get_user(new)).email

    def _schedule_email(
        self, background: BackgroundQueue, recipient: str | None, task: Task
    ) -> None:
        if recipient is not None:
            # Pass plain values; background delivery must not access request-scoped ORM/session.
            background.add_task(
                self.email.deliver_assignment, recipient, task.id, task.title
            )

    async def create(
        self,
        user: User,
        project: Project,
        data: TaskCreate,
        background: BackgroundQueue,
    ) -> Task:
        self.project_service.ensure_writable(project)
        if data.assignee_id is not None:
            await self._check_assignee(project.workspace_id, data.assignee_id)
        recipient = await self._recipient(user, data.assignee_id, None)
        async with transaction(self.repo.session):
            task = await self.repo.create(
                {**data.model_dump(), "project_id": project.id, "created_by": user.id}
            )
        await self.cache.invalidate(project.id)
        self._schedule_email(background, recipient, task)
        return task

    async def list_by_project(
        self,
        project: Project,
        pagination: Pagination,
        status: list[TaskStatus] | None,
        priority: list[TaskPriority] | None,
        assignee_id: int | None,
    ) -> Page[TaskRead]:
        lookup = await self.cache.lookup(
            project.id, pagination, status, priority, assignee_id
        )
        if lookup.payload is not None:
            try:
                return Page[TaskRead].model_validate_json(lookup.payload)
            except ValidationError:
                logger.warning(messages.CACHE_INVALID_PAYLOAD)
        items = await self.repo.list_by_project(
            project.id,
            pagination,
            status,
            priority,
            assignee_id,
        )
        page = Page[TaskRead](
            items=[TaskRead.model_validate(item) for item in items],
            total=await self.repo.count_by_project(
                project.id, status, priority, assignee_id
            ),
            skip=pagination.skip,
            limit=pagination.limit,
        )
        await self.cache.store(lookup, page.model_dump_json())
        return page

    async def update(
        self,
        access: AuthorizedResource[Task],
        data: TaskUpdate,
        user: User,
        background: BackgroundQueue,
    ) -> Task:
        changes = data.model_dump(exclude_unset=True)
        if changes.get("assignee_id") is not None:
            await self._check_assignee(
                access.project.workspace_id, changes["assignee_id"]
            )
        recipient = await self._recipient(
            user, changes.get("assignee_id"), access.resource.assignee_id
        )
        async with transaction(self.repo.session):
            task = await self.repo.update(access.resource, changes)
        await self.cache.invalidate(access.project.id)
        self._schedule_email(background, recipient, task)
        return task

    async def delete(self, user: User, access: AuthorizedResource[Task]) -> None:
        await self.policy.require_author_or_owner(
            user, access.resource.created_by, access.project
        )
        async with transaction(self.repo.session):
            await self.repo.delete(access.resource)
        await self.cache.invalidate(access.project.id)

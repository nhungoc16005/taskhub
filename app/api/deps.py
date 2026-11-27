from collections.abc import Awaitable, Callable
from functools import partial
from typing import Annotated, Protocol, TypeVar

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.cache import TaskCache
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.models.comment import Comment
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceRole
from app.repositories.comment_repository import CommentRepository
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.email_service import EmailService
from app.services.label_service import LabelService
from app.services.project_service import ProjectService
from app.services.resource_policy import AuthorizedResource
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    bearerFormat="JWT",
    auto_error=False,
    description="Đăng nhập tại /api/v1/auth/login, sau đó dán access_token vào đây (không thêm tiền tố Bearer).",
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_task_cache(request: Request) -> TaskCache:
    return request.app.state.task_cache


TaskCacheDep = Annotated[TaskCache, Depends(get_task_cache)]


def get_email_service() -> EmailService:
    return EmailService()


EmailServiceDep = Annotated[EmailService, Depends(get_email_service)]


def get_user_repo(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_refresh_token_repo(db: DbSession) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(repo)


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    token_repo: Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)],
) -> AuthService:
    return AuthService(user_repo, token_repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: AuthServiceDep,
) -> User:
    if credentials is None:
        raise UnauthorizedError(messages.COULD_NOT_VALIDATE)
    return await service.get_current_user(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise ForbiddenError()
    return user


AdminUser = Annotated[User, Depends(require_admin)]


# ---------- Workspace / Project (RBAC theo workspace_members) ----------


def get_workspace_service(
    db: DbSession,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    cache: TaskCacheDep,
) -> WorkspaceService:
    return WorkspaceService(
        WorkspaceRepository(db),
        WorkspaceMemberRepository(db),
        user_repo,
        TaskRepository(db),
        cache,
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_project_service(
    db: DbSession, workspace_service: WorkspaceServiceDep
) -> ProjectService:
    return ProjectService(ProjectRepository(db), workspace_service)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def require_workspace_role(
    required: WorkspaceRole,
) -> Callable[[int, User, WorkspaceService], Awaitable[Workspace]]:
    """Tạo dependency: đọc `workspace_id` từ path và kiểm tra quyền tối thiểu."""

    async def dependency(
        workspace_id: int, user: CurrentUser, service: WorkspaceServiceDep
    ) -> Workspace:
        return await service.get_with_role(user, workspace_id, required)

    return dependency


ResourceT = TypeVar("ResourceT")
ResourceCo = TypeVar("ResourceCo", covariant=True)


class ResourceLoader(Protocol[ResourceCo]):
    def __call__(
        self, required: WorkspaceRole, *, writable: bool = False
    ) -> Awaitable[ResourceCo]: ...


def require_role(
    loader: Callable[..., Awaitable[ResourceLoader[ResourceT]]],
    required: WorkspaceRole,
    *,
    writable: bool = False,
) -> Callable[[ResourceLoader[ResourceT]], Awaitable[ResourceT]]:
    """Apply one role/write policy to a typed resource loader dependency."""

    async def dependency(
        load: Annotated[ResourceLoader[ResourceT], Depends(loader)],
    ) -> ResourceT:
        return await load(required, writable=writable)

    return dependency


async def load_project(
    project_id: int, user: CurrentUser, service: ProjectServiceDep
) -> ResourceLoader[Project]:
    return partial(service.get_with_role, user, project_id)


ViewableWorkspace = Annotated[
    Workspace, Depends(require_workspace_role(WorkspaceRole.VIEWER))
]
EditableWorkspace = Annotated[
    Workspace, Depends(require_workspace_role(WorkspaceRole.EDITOR))
]
OwnedWorkspace = Annotated[
    Workspace, Depends(require_workspace_role(WorkspaceRole.OWNER))
]

ViewableProject = Annotated[
    Project, Depends(require_role(load_project, WorkspaceRole.VIEWER))
]
EditableProject = Annotated[
    Project, Depends(require_role(load_project, WorkspaceRole.EDITOR, writable=True))
]
OwnedProject = Annotated[
    Project, Depends(require_role(load_project, WorkspaceRole.OWNER, writable=True))
]


# ---------- Task / Label / Comment (quyền theo workspace chứa project) ----------


def get_task_service(
    db: DbSession,
    project_service: ProjectServiceDep,
    workspace_service: WorkspaceServiceDep,
    cache: TaskCacheDep,
    users: UserServiceDep,
    email: EmailServiceDep,
) -> TaskService:
    return TaskService(
        TaskRepository(db), project_service, workspace_service, cache, users, email
    )


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]


def get_label_service(
    db: DbSession, project_service: ProjectServiceDep
) -> LabelService:
    return LabelService(LabelRepository(db), project_service)


LabelServiceDep = Annotated[LabelService, Depends(get_label_service)]


def get_comment_service(db: DbSession, task_service: TaskServiceDep) -> CommentService:
    return CommentService(CommentRepository(db), task_service)


CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]


async def load_task(
    task_id: int, user: CurrentUser, service: TaskServiceDep
) -> ResourceLoader[AuthorizedResource[Task]]:
    return partial(service.get_with_role, user, task_id)


async def load_label(
    label_id: int, user: CurrentUser, service: LabelServiceDep
) -> ResourceLoader[AuthorizedResource[Label]]:
    return partial(service.get_with_role, user, label_id)


ViewableTask = Annotated[
    AuthorizedResource[Task], Depends(require_role(load_task, WorkspaceRole.VIEWER))
]
EditableTask = Annotated[
    AuthorizedResource[Task],
    Depends(require_role(load_task, WorkspaceRole.EDITOR, writable=True)),
]

EditableLabel = Annotated[
    AuthorizedResource[Label],
    Depends(require_role(load_label, WorkspaceRole.EDITOR, writable=True)),
]


async def get_deletable_comment(
    comment_id: int, user: CurrentUser, service: CommentServiceDep
) -> Comment:
    return await service.get_deletable(user, comment_id)


DeletableComment = Annotated[Comment, Depends(get_deletable_comment)]

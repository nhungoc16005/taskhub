from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.models.project import Project
from app.models.user import User, UserRole
from app.models.workspace import Workspace, WorkspaceRole
from app.repositories.project_repository import ProjectRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_member_repository import WorkspaceMemberRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[AsyncSession, Depends(get_db)]


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
    token: Annotated[str, Depends(oauth2_scheme)],
    service: AuthServiceDep,
) -> User:
    return await service.get_current_user(token)


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
) -> WorkspaceService:
    return WorkspaceService(
        WorkspaceRepository(db), WorkspaceMemberRepository(db), user_repo
    )


WorkspaceServiceDep = Annotated[WorkspaceService, Depends(get_workspace_service)]


def get_project_service(
    db: DbSession, workspace_service: WorkspaceServiceDep
) -> ProjectService:
    return ProjectService(ProjectRepository(db), workspace_service)


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def require_workspace_role(required: WorkspaceRole):
    """Tạo dependency: đọc `workspace_id` từ path và kiểm tra quyền tối thiểu."""

    async def dependency(
        workspace_id: int, user: CurrentUser, service: WorkspaceServiceDep
    ) -> Workspace:
        return await service.get_with_role(user, workspace_id, required)

    return dependency


def require_project_role(required: WorkspaceRole):
    """Tạo dependency: đọc `project_id` từ path và kiểm tra quyền trong workspace chứa nó."""

    async def dependency(
        project_id: int, user: CurrentUser, service: ProjectServiceDep
    ) -> Project:
        return await service.get_with_role(user, project_id, required)

    return dependency


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
    Project, Depends(require_project_role(WorkspaceRole.VIEWER))
]
EditableProject = Annotated[
    Project, Depends(require_project_role(WorkspaceRole.EDITOR))
]
OwnedProject = Annotated[Project, Depends(require_project_role(WorkspaceRole.OWNER))]

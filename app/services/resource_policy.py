from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.exceptions import NotFoundError, ProjectNotFoundError
from app.models.project import Project
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.services.project_service import ProjectService

T = TypeVar("T")


@dataclass(frozen=True)
class AuthorizedResource(Generic[T]):
    resource: T
    project: Project


class ProjectResourcePolicy:
    def __init__(self, projects: ProjectService):
        self.projects = projects

    async def load(
        self, loader: Callable[[int], Awaitable[T | None]], resource_id: int,
        user: User, required: WorkspaceRole, missing: type[NotFoundError],
        *, writable: bool = False,
    ) -> AuthorizedResource[T]:
        resource = await loader(resource_id)
        if resource is None:
            raise missing()
        try:
            project = await self.projects.get_with_role(
                user, resource.project_id, required, writable=writable
            )
        except ProjectNotFoundError:
            raise missing() from None
        return AuthorizedResource(resource, project)

    async def require_author_or_owner(
        self, user: User, author_id: int, project: Project
    ) -> None:
        if author_id != user.id:
            await self.projects.require_owner(user, project)

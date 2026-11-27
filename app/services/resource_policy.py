from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from app.core.exceptions import NotFoundError, ProjectNotFoundError
from app.models.project import Project
from app.models.user import User
from app.models.workspace import WorkspaceRole

if TYPE_CHECKING:
    from app.services.project_service import ProjectService

T = TypeVar("T")
P = TypeVar("P")


class ProjectChild(Protocol):
    @property
    def project_id(self) -> int: ...


ChildT = TypeVar("ChildT", bound=ProjectChild)


@dataclass(frozen=True)
class AuthorizedResource(Generic[T]):
    """Resource đã được nạp kèm project cha sau khi xác thực quyền."""

    resource: T
    project: Project


async def resolve_nested_resource(
    loader: Callable[[int], Awaitable[T | None]],
    resource_id: int,
    missing: type[NotFoundError],
    parent_verifier: Callable[[T], Awaitable[P]],
    parent_missing: type[NotFoundError],
) -> tuple[T, P]:
    """Helper DRY: Lấy resource con, xác thực quyền qua resource cha,

    và chuyển lỗi không tìm thấy của cha thành lỗi của con (tránh tiết lộ tài nguyên).
    """
    resource = await loader(resource_id)
    if resource is None:
        raise missing()
    try:
        parent = await parent_verifier(resource)
    except parent_missing:
        raise missing() from None
    return resource, parent


class ProjectResourcePolicy:
    """Chính sách phân quyền và nạp tài nguyên trực thuộc project (Task, Label)."""

    def __init__(self, projects: ProjectService):
        self.projects = projects

    async def load(
        self,
        loader: Callable[[int], Awaitable[ChildT | None]],
        resource_id: int,
        user: User,
        required: WorkspaceRole,
        missing: type[NotFoundError],
        *,
        writable: bool = False,
    ) -> AuthorizedResource[ChildT]:
        """Tải resource theo ID và kiểm tra vai trò người dùng trong workspace của project cha."""

        async def verify_parent(res: ChildT) -> Project:
            return await self.projects.get_with_role(
                user, res.project_id, required, writable=writable
            )

        resource, project = await resolve_nested_resource(
            loader, resource_id, missing, verify_parent, ProjectNotFoundError
        )
        return AuthorizedResource(resource, project)

    async def require_author_or_owner(
        self, user: User, author_id: int, project: Project
    ) -> None:
        """Chỉ cho phép tác giả thực hiện, hoặc chủ sở hữu workspace / admin."""
        if author_id != user.id:
            await self.projects.require_owner(user, project)

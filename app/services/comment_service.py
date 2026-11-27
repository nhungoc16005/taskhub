from app.core.exceptions import CommentNotFoundError, TaskNotFoundError
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.schemas.common import Page, Pagination
from app.services.resource_policy import resolve_nested_resource
from app.services.task_service import TaskService
from app.services.transaction import transaction


class CommentService:
    def __init__(self, repo: CommentRepository, task_service: TaskService):
        self.repo = repo
        self.task_service = task_service

    async def create(self, user: User, task: Task, data: CommentCreate) -> Comment:
        async with transaction(self.repo.session):
            return await self.repo.create(
                {"task_id": task.id, "author_id": user.id, "content": data.content}
            )

    async def list_by_task(self, task: Task, pagination: Pagination) -> Page[Comment]:
        return pagination.page(
            items=await self.repo.list_by_task(task.id, pagination),
            total=await self.repo.count_by_task(task.id),
        )

    async def get_deletable(self, user: User, comment_id: int) -> Comment:
        """Tác giả xóa comment của mình; OWNER/ADMIN xóa được comment của người khác."""
        comment, task = await resolve_nested_resource(
            self.repo.get,
            comment_id,
            CommentNotFoundError,
            lambda c: self.task_service.get_with_role(
                user, c.task_id, WorkspaceRole.EDITOR, writable=True
            ),
            TaskNotFoundError,
        )

        await self.task_service.policy.require_author_or_owner(
            user, comment.author_id, task.project
        )
        return comment

    async def delete(self, comment: Comment) -> None:
        async with transaction(self.repo.session):
            await self.repo.delete(comment)

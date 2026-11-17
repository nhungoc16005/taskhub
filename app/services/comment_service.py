from app.core.exceptions import CommentNotFoundError, TaskNotFoundError
from app.models.comment import Comment
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.task_service import TaskService


class CommentService:
    def __init__(self, repo: CommentRepository, task_service: TaskService):
        self.repo = repo
        self.task_service = task_service

    async def create(self, user: User, task: Task, data: CommentCreate) -> Comment:
        return await self.repo.create(
            {"task_id": task.id, "author_id": user.id, "content": data.content}
        )

    async def list_by_task(self, task: Task, skip: int, limit: int) -> dict:
        return {
            "items": await self.repo.list_by_task(task.id, skip, limit),
            "total": await self.repo.count_by_task(task.id),
            "skip": skip,
            "limit": limit,
        }

    async def delete(self, user: User, comment_id: int) -> None:
        """Tác giả xóa comment của mình; OWNER/ADMIN xóa được comment của người khác."""
        comment = await self.repo.get(comment_id)
        if comment is None:
            raise CommentNotFoundError()
        try:
            task = await self.task_service.get_with_role(
                user, comment.task_id, WorkspaceRole.VIEWER
            )
        except TaskNotFoundError:
            raise CommentNotFoundError()

        if comment.author_id != user.id:
            await self.task_service.require_owner(user, task)
        await self.repo.delete(comment)

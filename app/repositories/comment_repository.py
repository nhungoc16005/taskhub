from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Comment, session)

    async def list_by_task(
        self, task_id: int, skip: int, limit: int
    ) -> Sequence[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_task(self, task_id: int) -> int:
        stmt = (
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

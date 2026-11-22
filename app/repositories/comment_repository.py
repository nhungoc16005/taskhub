from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common import Pagination
from app.models.comment import Comment
from app.repositories.transactional import TransactionalRepository


class CommentRepository(TransactionalRepository[Comment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Comment, session)

    async def list_by_task(
        self, task_id: int, pagination: Pagination
    ) -> Sequence[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_task(self, task_id: int) -> int:
        stmt = (
            select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

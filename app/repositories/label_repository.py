from collections.abc import Sequence

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label, task_labels
from app.repositories.transactional import TransactionalRepository
from app.schemas.common import Pagination


class LabelRepository(TransactionalRepository[Label]):
    def __init__(self, session: AsyncSession):
        super().__init__(Label, session)

    async def list_by_project(
        self, project_id: int, pagination: Pagination
    ) -> Sequence[Label]:
        stmt = (
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def count_by_project(self, project_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(Label)
                .where(Label.project_id == project_id)
            )
            or 0
        )

    async def list_for_task(
        self, task_id: int, pagination: Pagination
    ) -> Sequence[Label]:
        stmt = (
            select(Label)
            .join(task_labels, task_labels.c.label_id == Label.id)
            .where(task_labels.c.task_id == task_id)
            .order_by(Label.id)
            .offset(pagination.skip)
            .limit(pagination.limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def count_for_task(self, task_id: int) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(task_labels)
                .where(task_labels.c.task_id == task_id)
            )
            or 0
        )

    async def is_attached(self, task_id: int, label_id: int) -> bool:
        stmt = select(task_labels.c.task_id).where(
            task_labels.c.task_id == task_id, task_labels.c.label_id == label_id
        )
        return (await self.session.execute(stmt)).first() is not None

    async def attach(self, task_id: int, label_id: int) -> None:
        await self.session.execute(
            insert(task_labels).values(task_id=task_id, label_id=label_id)
        )
        await self.session.flush()

    async def detach(self, task_id: int, label_id: int) -> None:
        await self.session.execute(
            delete(task_labels).where(
                task_labels.c.task_id == task_id, task_labels.c.label_id == label_id
            )
        )
        await self.session.flush()

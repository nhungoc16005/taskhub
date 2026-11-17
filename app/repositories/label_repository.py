from collections.abc import Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label, task_labels
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession):
        super().__init__(Label, session)

    async def list_by_project(self, project_id: int) -> Sequence[Label]:
        stmt = select(Label).where(Label.project_id == project_id).order_by(Label.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_task(self, task_id: int) -> Sequence[Label]:
        stmt = (
            select(Label)
            .join(task_labels, task_labels.c.label_id == Label.id)
            .where(task_labels.c.task_id == task_id)
            .order_by(Label.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def is_attached(self, task_id: int, label_id: int) -> bool:
        stmt = select(task_labels.c.task_id).where(
            task_labels.c.task_id == task_id, task_labels.c.label_id == label_id
        )
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def attach(self, task_id: int, label_id: int) -> None:
        try:
            await self.session.execute(
                insert(task_labels).values(task_id=task_id, label_id=label_id)
            )
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise

    async def detach(self, task_id: int, label_id: int) -> None:
        await self.session.execute(
            delete(task_labels).where(
                task_labels.c.task_id == task_id, task_labels.c.label_id == label_id
            )
        )
        await self.session.commit()

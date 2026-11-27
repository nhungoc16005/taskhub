from app.repositories.base import BaseRepository, ModelT


class TransactionalRepository(BaseRepository[ModelT]):
    """Reuse CRUD while the service owns commit/rollback for a multi-step write."""

    async def _persist(self) -> None:
        await self.session.flush()

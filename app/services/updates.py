from pydantic import BaseModel

from app.repositories.base import BaseRepository, ModelT


async def update_from_schema(
    repo: BaseRepository[ModelT], resource: ModelT, data: BaseModel
) -> ModelT:
    """Convert PATCH input in the service layer; repositories accept plain data."""
    return await repo.update(resource, data.model_dump(exclude_unset=True))

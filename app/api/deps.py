from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repo(db: DbSession) -> UserRepository:
    return UserRepository(db)


def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]

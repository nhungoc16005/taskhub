from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


@lru_cache  # Day 1: repo in-memory phải là singleton, nếu không sẽ mất dữ liệu
def get_user_repo() -> UserRepository:
    return UserRepository()


def get_user_service(
    repo: Annotated[UserRepository, Depends(get_user_repo)],
) -> UserService:
    return UserService(repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]

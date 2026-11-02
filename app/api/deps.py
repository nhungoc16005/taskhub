from functools import lru_cache
from fastapi import Depends
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


@lru_cache
def get_user_repo() -> UserRepository:
    return UserRepository()


def get_user_service(repo: UserRepository = Depends(get_user_repo)) -> UserService:
    return UserService(repo)

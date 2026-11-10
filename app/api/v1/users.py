from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import UserServiceDep
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.user import Page, UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, service: UserServiceDep):
    return service.create_user(data)


@router.get("", response_model=Page[UserRead])
def list_users(
    service: UserServiceDep, skip: Skip = 0, limit: Limit = DEFAULT_PAGE_SIZE
):
    return service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, service: UserServiceDep):
    return service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserUpdate, service: UserServiceDep):
    return service.update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, service: UserServiceDep):
    service.delete_user(user_id)

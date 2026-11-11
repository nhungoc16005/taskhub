from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    AdminUser,
    AuthServiceDep,
    CurrentUser,
    UserServiceDep,
    get_current_user,
)
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.user import ChangePasswordRequest, Page, UserRead, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate, current_user: CurrentUser, service: UserServiceDep
):
    return await service.update_user(current_user.id, data)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest, current_user: CurrentUser, service: AuthServiceDep
):
    await service.change_password(
        current_user, data.current_password, data.new_password
    )


@router.get("", response_model=Page[UserRead])
async def list_users(
    service: UserServiceDep, skip: Skip = 0, limit: Limit = DEFAULT_PAGE_SIZE
):
    return await service.list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(user_id: int, service: UserServiceDep):
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int, data: UserUpdate, _admin: AdminUser, service: UserServiceDep
):
    return await service.update_user(user_id, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, _admin: AdminUser, service: UserServiceDep):
    await service.delete_user(user_id)

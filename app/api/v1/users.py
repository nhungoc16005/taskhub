from fastapi import APIRouter, Depends, status

from app.api.deps import (
    AdminUser,
    AuthServiceDep,
    CurrentUser,
    UserServiceDep,
    get_current_user,
)
from app.api.pagination import PaginationDep
from app.api.responses import error_responses
from app.schemas.common import Page
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get my profile",
    responses=error_responses(
        401, 403, 500, descriptions={403: "Inactive user or insufficient permissions"}
    ),
)
async def read_me(current_user: CurrentUser):
    return current_user


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update my profile",
    responses=error_responses(
        401,
        403,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def update_me(
    data: UserUpdate, current_user: CurrentUser, service: UserServiceDep
):
    return await service.update_user(current_user.id, data)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change my password",
    responses=error_responses(
        400,
        401,
        403,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def change_password(
    data: ChangePasswordRequest, current_user: CurrentUser, service: AuthServiceDep
):
    await service.change_password(
        current_user, data.current_password, data.new_password
    )


@router.get(
    "",
    response_model=Page[UserRead],
    summary="List users",
    responses=error_responses(
        401,
        403,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def list_users(service: UserServiceDep, pagination: PaginationDep):
    return await service.list_users(pagination)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get a user",
    responses=error_responses(
        401,
        403,
        404,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def get_user(user_id: int, service: UserServiceDep):
    return await service.get_user(user_id)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    summary="Update a user as admin",
    responses=error_responses(
        401,
        403,
        404,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def update_user(
    user_id: int, data: UserUpdate, _admin: AdminUser, service: UserServiceDep
):
    return await service.update_user(user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user as admin",
    responses=error_responses(
        401,
        403,
        404,
        409,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def delete_user(user_id: int, _admin: AdminUser, service: UserServiceDep):
    await service.delete_user(user_id)

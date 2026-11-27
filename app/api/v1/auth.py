from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep, UserServiceDep
from app.api.documentation import LOGIN_EXAMPLE, REGISTER_EXAMPLE
from app.api.responses import error_responses
from app.schemas.auth import AccessTokenResponse, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a user",
    responses=error_responses(409, 422, 500),
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": REGISTER_EXAMPLE}}}
    },
)
async def register(data: UserCreate, service: UserServiceDep):
    return await service.create_user(data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in using email and password",
    description="Gửi form application/x-www-form-urlencoded; username là email. Dùng access_token trả về trong nút Authorize.",
    responses=error_responses(401, 403, 422, 500),
    openapi_extra={
        "requestBody": {
            "content": {"application/x-www-form-urlencoded": {"example": LOGIN_EXAMPLE}}
        }
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: AuthServiceDep,
):
    return await service.login(form_data.username, form_data.password)


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh an access token",
    responses=error_responses(401, 422, 500),
)
async def refresh(data: RefreshRequest, service: AuthServiceDep):
    return await service.refresh(data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
    responses=error_responses(401, 422, 500),
)
async def logout(data: RefreshRequest, service: AuthServiceDep):
    await service.logout(data.refresh_token)

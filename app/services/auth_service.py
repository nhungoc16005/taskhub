from datetime import datetime, timezone

from app.core import messages
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, TOKEN_TYPE_BEARER
from app.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidTokenError,
)
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository, token_repo: RefreshTokenRepository):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    async def login(self, email: str, password: str) -> dict:
        user = await self.authenticate(email, password)

        refresh_token = create_refresh_token(user.id)
        payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        await self.token_repo.create(
            {
                "user_id": user.id,
                "jti": payload["jti"],
                "expires_at": datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            }
        )
        return {
            "access_token": create_access_token(user.id),
            "refresh_token": refresh_token,
            "token_type": TOKEN_TYPE_BEARER,
        }

    async def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token, ACCESS_TOKEN_TYPE)
            user_id = int(payload["sub"])
        except (TokenError, KeyError, ValueError):
            raise InvalidCredentialsError(messages.COULD_NOT_VALIDATE)

        user = await self.user_repo.get(user_id)
        if user is None:
            raise InvalidCredentialsError(messages.COULD_NOT_VALIDATE)
        if not user.is_active:
            raise InactiveUserError()
        return user

    async def refresh(self, refresh_token: str) -> dict:
        record = await self._get_valid_record(refresh_token)
        user = await self.user_repo.get(record.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError()
        return {
            "access_token": create_access_token(user.id),
            "token_type": TOKEN_TYPE_BEARER,
        }

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        except TokenError:
            raise InvalidTokenError()

        record = await self.token_repo.get_by_jti(payload["jti"])
        if record is not None and record.revoked_at is None:
            await self.token_repo.revoke(record)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidPasswordError(messages.CURRENT_PASSWORD_INCORRECT)
        if verify_password(new_password, user.hashed_password):
            raise InvalidPasswordError(messages.NEW_PASSWORD_SAME_AS_CURRENT)

        await self.user_repo.update(
            user, {"hashed_password": hash_password(new_password)}
        )
        await self.token_repo.revoke_all_for_user(user.id)

    async def _get_valid_record(self, refresh_token: str) -> RefreshToken:
        try:
            payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        except TokenError:
            raise InvalidTokenError()

        record = await self.token_repo.get_by_jti(payload["jti"])
        if record is None or record.revoked_at is not None:
            raise InvalidTokenError()
        # SQLite trả datetime không có timezone, PostgreSQL thì có
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise InvalidTokenError()
        return record

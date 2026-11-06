from datetime import datetime, timezone

from app.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidPasswordError,
    InvalidTokenError,
)
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
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
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ):
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Incorrect email or password")
        if not user.is_active:
            raise InactiveUserError("Inactive user")
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
            "token_type": "bearer",
        }

    async def get_current_user(self, token: str) -> User:
        try:
            payload = decode_token(token, ACCESS_TOKEN_TYPE)
            user_id = int(payload["sub"])
        except (TokenError, KeyError, ValueError):
            raise InvalidCredentialsError("Could not validate credentials")

        user = await self.user_repo.get(user_id)
        if user is None:
            raise InvalidCredentialsError("Could not validate credentials")
        if not user.is_active:
            raise InactiveUserError("Inactive user")
        return user

    async def refresh(self, refresh_token: str) -> dict:
        record = await self._get_valid_record(refresh_token)

        user = await self.user_repo.get(record.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError("Invalid refresh token")

        return {"access_token": create_access_token(user.id), "token_type": "bearer"}

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        except TokenError:
            raise InvalidTokenError("Invalid refresh token")

        record = await self.token_repo.get_by_jti(payload["jti"])
        if record is not None and record.revoked_at is None:
            await self.token_repo.revoke(record)

    async def _get_valid_record(self, refresh_token: str) -> RefreshToken:
        try:
            payload = decode_token(refresh_token, REFRESH_TOKEN_TYPE)
        except TokenError:
            raise InvalidTokenError("Invalid refresh token")

        record = await self.token_repo.get_by_jti(payload["jti"])
        now = datetime.now(timezone.utc)
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            raise InvalidTokenError("Invalid refresh token")
        return record

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidPasswordError("Current password is incorrect")
        if verify_password(new_password, user.hashed_password):
            raise InvalidPasswordError(
                "New password must be different from the current password"
            )

        await self.user_repo.update(
            user, {"hashed_password": hash_password(new_password)}
        )
        await self.token_repo.revoke_all_for_user(user.id)

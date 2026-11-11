import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core import messages
from app.core.config import settings
from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE


class TokenError(Exception):
    """Token sai chữ ký, hết hạn, hỏng định dạng hoặc sai loại."""


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        str(user_id),
        ACCESS_TOKEN_TYPE,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id),
        REFRESH_TOKEN_TYPE,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise TokenError(messages.TOKEN_EXPIRED)
    except jwt.InvalidTokenError:
        raise TokenError(messages.TOKEN_INVALID)

    if payload.get("type") != expected_type:
        raise TokenError(messages.TOKEN_WRONG_TYPE)
    return payload

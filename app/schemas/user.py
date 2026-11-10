from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, EmailStr, Field, StringConstraints, field_validator
from pydantic import ConfigDict
from app.core.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    FULL_NAME_MIN_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
)

FullName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=FULL_NAME_MIN_LENGTH,
        max_length=FULL_NAME_MAX_LENGTH,
    ),
]


class UserCreate(BaseModel):
    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH)
    full_name: FullName = Field(..., description="The full name of the user")
    password: str = Field(
        ..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_BYTES
    )

    @field_validator("password")
    @classmethod
    def password_max_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > PASSWORD_MAX_BYTES:
            raise ValueError(f"Password must be at most {PASSWORD_MAX_BYTES} bytes")
        return v


class UserUpdate(BaseModel):
    full_name: FullName | None = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_null(cls, v):
        if v is None:
            raise ValueError("full_name cannot be null")
        return v


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    model_config = ConfigDict(from_attributes=True)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

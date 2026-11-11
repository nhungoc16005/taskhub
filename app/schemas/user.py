from typing import Annotated, Generic, TypeVar

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.core.constants import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    FULL_NAME_MIN_LENGTH,
    PASSWORD_MAX_BYTES,
    PASSWORD_MIN_LENGTH,
)
from app.models.user import UserRole

FullName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=FULL_NAME_MIN_LENGTH,
        max_length=FULL_NAME_MAX_LENGTH,
    ),
]


def _check_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > PASSWORD_MAX_BYTES:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_BYTES} bytes")
    return value


Password = Annotated[
    str,
    Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_BYTES),
    AfterValidator(_check_password_bytes),
]


class UserCreate(BaseModel):
    email: EmailStr = Field(..., max_length=EMAIL_MAX_LENGTH)
    full_name: FullName = Field(..., description="The full name of the user")
    password: Password = Field(..., description="The password for the user account")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ..., min_length=1, description="The user's current password"
    )
    new_password: Password = Field(..., description="The new password")


class UserUpdate(BaseModel):
    full_name: FullName | None = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_null(cls, v):
        if v is None:
            raise ValueError("full_name cannot be null")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

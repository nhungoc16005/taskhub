from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _check_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return value


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user")
    full_name: str = Field(..., description="The full name of the user")
    password: str = Field(
        ..., min_length=8, description="The password for the user account"
    )

    @field_validator("password")
    @classmethod
    def password_max_72_bytes(cls, value: str) -> str:
        return _check_password_bytes(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="The user's current password")
    new_password: str = Field(
        ..., min_length=8, description="The new password (8 characters or more)"
    )

    @field_validator("new_password")
    @classmethod
    def new_password_max_72_bytes(cls, value: str) -> str:
        return _check_password_bytes(value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="The unique identifier of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    full_name: str = Field(..., description="The full name of the user")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, description="The full name of the user")

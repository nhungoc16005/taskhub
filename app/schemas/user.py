from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="The email address of the user")
    full_name: str = Field(..., description="The full name of the user")
    password: str = Field(
        ..., min_length=8, description="The password for the user account"
    )


class UserRead(BaseModel):
    id: int = Field(..., description="The unique identifier of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    full_name: str = Field(..., description="The full name of the user")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, description="The full name of the user")

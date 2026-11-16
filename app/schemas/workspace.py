from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import EMAIL_MAX_LENGTH
from app.models.workspace import WorkspaceRole
from app.schemas.common import NameStr


class WorkspaceCreate(BaseModel):
    name: NameStr = Field(..., description="The workspace name")


class WorkspaceUpdate(BaseModel):
    name: NameStr | None = None

    @field_validator("name")
    @classmethod
    def name_not_null(cls, v):
        if v is None:
            raise ValueError("name cannot be null")
        return v


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime


class MemberInvite(BaseModel):
    email: EmailStr = Field(
        ..., max_length=EMAIL_MAX_LENGTH, description="Email of the user to invite"
    )
    # OWNER không mời được: mỗi workspace chỉ có 1 owner (người tạo)
    role: Literal[WorkspaceRole.EDITOR, WorkspaceRole.VIEWER] = Field(
        WorkspaceRole.VIEWER, description="Role granted in the workspace"
    )


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    role: WorkspaceRole

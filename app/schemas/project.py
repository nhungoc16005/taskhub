from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DESCRIPTION_MAX_LENGTH
from app.models.project import ProjectStatus
from app.schemas.common import NameStr


class ProjectCreate(BaseModel):
    name: NameStr = Field(..., description="The project name")
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)


class ProjectUpdate(BaseModel):
    name: NameStr | None = None
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def name_not_null(cls, v):
        if v is None:
            raise ValueError("name cannot be null")
        return v


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DESCRIPTION_MAX_LENGTH
from app.core.enums import ProjectStatus
from app.schemas.common import NameStr, UpdateName


class ProjectCreate(BaseModel):
    name: NameStr = Field(..., description="The project name")
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)


class ProjectUpdate(BaseModel):
    name: UpdateName = None
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime

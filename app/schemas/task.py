from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DESCRIPTION_MAX_LENGTH
from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import NameStr


class TaskCreate(BaseModel):
    title: NameStr = Field(..., description="The task title")
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: date | None = Field(None, description="Due date (YYYY-MM-DD)")
    assignee_id: int | None = Field(None, description="Id of a workspace member")


class TaskUpdate(BaseModel):
    title: NameStr | None = None
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assignee_id: int | None = None  # null = bỏ gán

    @field_validator("title", "status", "priority")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("this field cannot be null")
        return v


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    assignee_id: int | None
    created_by: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    created_at: datetime

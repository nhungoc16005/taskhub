from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from app.core.constants import DESCRIPTION_MAX_LENGTH
from app.core.enums import TaskPriority, TaskStatus
from app.core.messages import DUE_DATE_IN_PAST
from app.schemas.common import NameStr, NonNull


class TaskCreate(BaseModel):
    title: NameStr = Field(..., description="The task title")
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    due_date: date | None = Field(None, description="Due date (YYYY-MM-DD)")
    assignee_id: PositiveInt | None = Field(None, description="Id of a workspace member")


    @field_validator("due_date")
    @classmethod
    def due_date_not_in_past(cls, value: date | None) -> date | None:
        # Date-only API uses UTC consistently, independent of server timezone.
        if value is not None and value < datetime.now(UTC).date():
            raise ValueError(DUE_DATE_IN_PAST)
        return value


class TaskUpdate(BaseModel):
    title: NonNull[NameStr] = None
    description: str | None = Field(None, max_length=DESCRIPTION_MAX_LENGTH)
    status: NonNull[TaskStatus] = None
    priority: NonNull[TaskPriority] = None
    due_date: date | None = None
    assignee_id: PositiveInt | None = None  # null = bỏ gán



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

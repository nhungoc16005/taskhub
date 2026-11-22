from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.constants import COMMENT_MAX_LENGTH

CommentContent = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=COMMENT_MAX_LENGTH
    ),
]


class CommentCreate(BaseModel):
    content: CommentContent = Field(..., description="The comment text")


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime

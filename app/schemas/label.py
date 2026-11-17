from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.core.constants import (
    DEFAULT_LABEL_COLOR,
    HEX_COLOR_PATTERN,
    LABEL_NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)

LabelName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=NAME_MIN_LENGTH,
        max_length=LABEL_NAME_MAX_LENGTH,
    ),
]
HexColor = Annotated[str, StringConstraints(pattern=HEX_COLOR_PATTERN)]


class LabelCreate(BaseModel):
    name: LabelName = Field(..., description="The label name")
    color: HexColor = Field(DEFAULT_LABEL_COLOR, description="Hex color, e.g. #FF0000")


class LabelUpdate(BaseModel):
    name: LabelName | None = None
    color: HexColor | None = None

    @field_validator("name", "color")
    @classmethod
    def not_null(cls, v):
        if v is None:
            raise ValueError("this field cannot be null")
        return v


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str

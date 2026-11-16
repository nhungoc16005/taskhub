from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, StringConstraints

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH

NameStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    ),
]

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

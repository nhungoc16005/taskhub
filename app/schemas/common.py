from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.core.constants import NAME_MAX_LENGTH, NAME_MIN_LENGTH
from app.core.messages import NAME_CANNOT_BE_NULL

NameStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=NAME_MIN_LENGTH,
        max_length=NAME_MAX_LENGTH,
    ),
]

T = TypeVar("T")


def name_not_null(value: str | None) -> str:
    if value is None:
        raise ValueError(NAME_CANNOT_BE_NULL)
    return value


# A missing PATCH field is allowed; an explicitly supplied null is rejected.
UpdateName = Annotated[NameStr | None, AfterValidator(name_not_null)]


class Page(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True)
class Pagination:
    skip: int
    limit: int

    def page(self, items: Sequence[T], total: int) -> Page[T]:
        return Page(items=list(items), total=total, skip=self.skip, limit=self.limit)

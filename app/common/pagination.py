from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from bson import ObjectId


T = TypeVar('T')


def parse_limit(value: object) -> int:
    if isinstance(value, str) and value.isascii() and value.isdigit():
        digits = value.lstrip('0') or '0'
        value = int(digits) if len(digits) <= 3 else 101
    if type(value) is not int or not 1 <= value <= 100:
        raise ValueError('limit must be an integer between 1 and 100')
    return value


@dataclass(frozen=True)
class PaginationParams:
    limit: int = 20
    cursor: ObjectId | None = None

    def __post_init__(self):
        if type(self.limit) is not int:
            raise ValueError('limit must be an integer between 1 and 100')
        parse_limit(self.limit)


@dataclass
class Page(Generic[T]):
    data: list[T]
    next: str | None
    limit: int
    has_more: bool


def paginate(items: Sequence[T], params: PaginationParams, *, key: Callable[[T], object]) -> Page[T]:
    has_more = len(items) > params.limit
    data = list(items[:params.limit])
    return Page(
        data=data, next=str(key(data[-1])) if has_more else None,
        limit=params.limit, has_more=has_more,
    )

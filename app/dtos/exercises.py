from dataclasses import dataclass, fields
from string import hexdigits
from urllib.parse import urlsplit

from app.common.pagination import PaginationParams, parse_limit
from app.dtos.base import BaseDTO, DTOValidationError
from app.dtos.utils import validate_object_id
from app.models.exercise import DESCRIPTION_MAX_LENGTH, EQUIPMENT, MUSCLE_GROUPS, NAME_MAX_LENGTH


def _array_error(name: str, values: list[str], allowed: tuple[str, ...]) -> str | None:
    if not values:
        return f'{name} must contain at least 1 item'
    if any(not isinstance(value, str) or value not in allowed for value in values):
        return f'{name} must contain only allowed values: {", ".join(allowed)}'
    return None


def _valid_uri(value: str) -> bool:
    if not value or not value.isascii() or any(not char.isprintable() or char.isspace() or char in '<>"{}|\\^`' for char in value):
        return False
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    if not parts.scheme or parts.netloc.count('@') > 1:
        return False
    authority = parts.netloc.rsplit('@', 1)[-1]
    if authority.startswith('['):
        suffix = authority[authority.index(']') + 1:]
    else:
        suffix = authority[authority.index(':'):] if ':' in authority else ''
    if suffix and (not suffix.startswith(':') or (suffix[1:] and not suffix[1:].isdigit())):
        return False
    if any(char in part for part in (parts.path, parts.query, parts.fragment) for char in '[]') or '#' in parts.fragment:
        return False
    return all(len(segment) >= 2 and all(char in hexdigits for char in segment[:2]) for segment in value.split('%')[1:])


class _ExerciseValidation(BaseDTO):
    no_strip_fields = frozenset({'description', 'video_url', 'image_url'})

    def _validate_name(self, value: str) -> str | None:
        if not value:
            return 'name cannot be blank'
        if len(value) > NAME_MAX_LENGTH:
            return f'name must be at most {NAME_MAX_LENGTH} characters'
        return None

    def _validate_description(self, value: str) -> str | None:
        return f'description must be at most {DESCRIPTION_MAX_LENGTH} characters' if len(value) > DESCRIPTION_MAX_LENGTH else None

    def _validate_muscle_groups(self, value: list[str]) -> str | None:
        return _array_error('muscle_groups', value, MUSCLE_GROUPS)

    def _validate_equipment(self, value: list[str]) -> str | None:
        return _array_error('equipment', value, EQUIPMENT)

    def _validate_video_url(self, value: str) -> str | None:
        return None if _valid_uri(value) else 'video_url must be a valid URI'

    def _validate_image_url(self, value: str) -> str | None:
        return None if _valid_uri(value) else 'image_url must be a valid URI'

    def to_document(self) -> dict[str, object]:
        return {item.name: getattr(self, item.name) for item in fields(self) if getattr(self, item.name) is not None}


@dataclass
class ExerciseCreateDTO(_ExerciseValidation):
    name: str
    muscle_groups: list[str]
    equipment: list[str]
    description: str | None = None
    video_url: str | None = None
    image_url: str | None = None


@dataclass
class ExerciseUpdateDTO(_ExerciseValidation):
    name: str | None = None
    muscle_groups: list[str] | None = None
    equipment: list[str] | None = None
    description: str | None = None
    video_url: str | None = None
    image_url: str | None = None


@dataclass
class ExerciseListDTO(BaseDTO):
    no_strip_fields = frozenset({'search', 'cursor', 'limit'})
    muscle_group: str | None = None
    equipment: str | None = None
    search: str | None = None
    cursor: str | None = None
    limit: str = '20'

    def _validate_muscle_group(self, value: str) -> str | None:
        values = [item.strip().upper() for item in value.split(',')]
        self.muscle_group = ','.join(values)
        return _array_error('muscle_group', values, MUSCLE_GROUPS)

    def _validate_equipment(self, value: str) -> str | None:
        values = [item.strip().upper() for item in value.split(',')]
        self.equipment = ','.join(values)
        return _array_error('equipment', values, EQUIPMENT)

    def _validate_cursor(self, value: str) -> str | None:
        try:
            validate_object_id(value, 'cursor')
        except DTOValidationError:
            return 'cursor must be a valid exercise cursor'
        return None

    def _validate_limit(self, value: str) -> str | None:
        try:
            parse_limit(value)
        except ValueError as exc:
            return str(exc)
        return None

    @property
    def pagination(self) -> PaginationParams:
        return PaginationParams(
            limit=parse_limit(self.limit),
            cursor=validate_object_id(self.cursor, 'cursor') if self.cursor is not None else None,
        )

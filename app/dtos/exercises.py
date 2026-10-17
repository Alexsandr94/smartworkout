from dataclasses import dataclass, fields
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
    if (
        not isinstance(value, str)
        or not value
        or not value.isascii()
        or not value.isprintable()
        or any(char.isspace() for char in value)
    ):
        return False

    try:
        parts = urlsplit(value)

        if not parts.scheme:
            return False

        if parts.scheme.lower() in ("http", "https"):
            return bool(parts.hostname) and (
                parts.port is None or parts.port > 0
            )

        return bool(parts.netloc or parts.path)

    except ValueError:
        return False


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

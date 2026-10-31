from dataclasses import dataclass, fields
from app.dtos.base import BaseDTO, DTOValidationError
from app.dtos.utils import validate_object_id
from app.common.pagination import PaginationParams, parse_limit

@dataclass
class ProgramExerciseDTO(BaseDTO):
    exercise_id: str
    order: int
    sets: int
    reps: int
    rest_sec: int

    def _validate_exercise_id(self, value: str) -> str | None:
        try:
            validate_object_id(value, "exercise_id")
        except DTOValidationError:
            return "invalid exercise_id format"
        return None

    def _validate_order(self, value: int) -> str | None:
        if value <= 0:
            return "order must be greater than 0"
        return None

    def _validate_sets(self, value: int) -> str | None:
        if value <= 0:
            return "sets must be greater than 0"
        return None

    def _validate_reps(self, value: int) -> str | None:
        if value <= 0:
            return "reps must be greater than 0"
        return None

    def _validate_rest_sec(self, value: int) -> str | None:
        if value < 0:
            return "rest_sec cannot be negative"
        return None

    def to_document(self) -> dict:
        return {item.name: getattr(self, item.name) for item in fields(self)}


@dataclass
class ProgramCreateDTO(BaseDTO):
    title: str
    is_public: bool
    exercises: list[ProgramExerciseDTO]
    difficulty: str
    description: str = ""

    def _validate_title(self, value: str) -> str | None:
        if not (1 <= len(value) <= 200):
            return "title must be between 1 and 200 characters"
        return None

    def _validate_description(self, value: str) -> str | None:
        if len(value) > 2000:
            return "description must be at most 2000 characters"
        return None

    def _validate_difficulty(self, value: str) -> str | None:
        allowed = ("Beginner", "Intermediate", "Advanced")
        if value not in allowed:
            return f"difficulty must be one of: {', '.join(allowed)}"
        return None

    def __post_init__(self):
        super().__post_init__()

        if not self.exercises:
            raise DTOValidationError([{"field": "exercises", "message": "at least one exercise is required"}])

        validated = []
        errors = []
        for idx, ex in enumerate(self.exercises):
            if not isinstance(ex, dict):
                errors.append({"field": f"exercises.{idx}", "message": "must be an object"})
                continue
            try:
                validated.append(ProgramExerciseDTO.from_dict(ex))
            except DTOValidationError as exc:
                for err in exc.errors:
                    errors.append({"field": f"exercises.{idx}.{err['field']}", "message": err["message"]})

        if errors:
            raise DTOValidationError(errors)
        self.exercises = validated

    def to_document(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "is_public": self.is_public,
            "difficulty": self.difficulty,
            "exercises": [ex.to_document() for ex in self.exercises]
        }


@dataclass
class ProgramUpdateDTO(BaseDTO):
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None
    exercises: list[ProgramExerciseDTO] | None = None

    def _validate_title(self, value: str) -> str | None:
        if not (1 <= len(value) <= 200):
            return "title must be between 1 and 200 characters"
        return None

    def _validate_description(self, value: str) -> str | None:
        if len(value) > 2000:
            return "description must be at most 2000 characters"
        return None

    def _validate_difficulty(self, value: str) -> str | None:
        allowed = ("Beginner", "Intermediate", "Advanced")
        if value not in allowed:
            return f"difficulty must be one of: {', '.join(allowed)}"
        return None

    def __post_init__(self):
        if all(getattr(self, f) is None for f in ("title", "description", "difficulty", "exercises")):
            raise DTOValidationError([{"field": "body", "message": "at least one field must be provided for update"}])

        super().__post_init__()

        if self.exercises is not None:
            if not self.exercises:
                raise DTOValidationError([{"field": "exercises", "message": "at least one exercise is required"}])

            validated = []
            errors = []
            for idx, ex in enumerate(self.exercises):
                if not isinstance(ex, dict):
                    errors.append({"field": f"exercises.{idx}", "message": "must be an object"})
                    continue
                try:
                    validated.append(ProgramExerciseDTO.from_dict(ex))
                except DTOValidationError as exc:
                    for err in exc.errors:
                        errors.append({"field": f"exercises.{idx}.{err['field']}", "message": err["message"]})

            if errors:
                raise DTOValidationError(errors)
            self.exercises = validated

    def to_document(self) -> dict:
        doc = {}
        if self.title is not None: doc["title"] = self.title
        if self.description is not None: doc["description"] = self.description
        if self.difficulty is not None: doc["difficulty"] = self.difficulty
        if self.exercises is not None:
            doc["exercises"] = [ex.to_document() for ex in self.exercises]
        return doc

@dataclass
class ProgramListDTO(BaseDTO):
    no_strip_fields = frozenset({'cursor', 'limit'})
    cursor: str | None = None
    limit: str = '20'

    def _validate_cursor(self, value: str) -> str | None:
        try:
            validate_object_id(value, 'cursor')
        except DTOValidationError:
            return 'cursor must be a valid program cursor'
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
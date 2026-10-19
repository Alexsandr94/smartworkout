from dataclasses import dataclass
from app.dtos.base import BaseDTO
from app.dtos.utils import validate_object_id, DTOValidationError

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


@dataclass
class ProgramDTO(BaseDTO):
    title: str
    is_public: bool
    exercises: list[ProgramExerciseDTO] # Используем наш переименованный класс
    description: str = ""
    difficulty: str = ""

    def _validate_title(self, value: str) -> str | None:
        if len(value) < 3:
            return "title must be at least 3 characters long"
        return None

    def _validate_exercises(self, value: list) -> str | None:
        if not value:
            return "at least one exercise is required"
        return None
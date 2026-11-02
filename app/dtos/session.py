from dataclasses import dataclass, field, fields

from app.dtos.base import BaseDTO, DTOValidationError
from app.dtos.utils import validate_object_id


@dataclass
class SessionStartExerciseDTO(BaseDTO):
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
class SessionStartDTO(BaseDTO):
    program_id: str
    exercises: list[SessionStartExerciseDTO] | None = None

    def _validate_program_id(self, value: str) -> str | None:
        try:
            validate_object_id(value, "program_id")
        except DTOValidationError:
            return "invalid program_id format"
        return None

    def __post_init__(self):
        super().__post_init__()

        if self.exercises is None:
            return

        if not self.exercises:
            raise DTOValidationError([
                {
                    "field": "exercises",
                    "message": "at least one exercise is required when exercises is provided",
                }
            ])

        validated = []
        errors = []

        for index, exercise in enumerate(self.exercises):
            if not isinstance(exercise, dict):
                errors.append({
                    "field": f"exercises.{index}",
                    "message": "must be an object",
                })
                continue

            try:
                validated.append(SessionStartExerciseDTO.from_dict(exercise))
            except DTOValidationError as exc:
                for error in exc.errors:
                    errors.append({
                        "field": f"exercises.{index}.{error['field']}",
                        "message": error["message"],
                    })

        if errors:
            raise DTOValidationError(errors)

        self.exercises = validated

    def exercises_document(self) -> list[dict] | None:
        if self.exercises is None:
            return None
        return [exercise.to_document() for exercise in self.exercises]


@dataclass
class SessionFinishExerciseDTO(BaseDTO):
    exercise_id: str
    completed_sets: int
    actual_reps: list[int]
    is_completed: bool
    is_skipped: bool

    def _validate_exercise_id(self, value: str) -> str | None:
        try:
            validate_object_id(value, "exercise_id")
        except DTOValidationError:
            return "invalid exercise_id format"
        return None

    def _validate_completed_sets(self, value: int) -> str | None:
        if value < 0:
            return "completed_sets cannot be negative"
        return None

    def _validate_actual_reps(self, value: list[int]) -> str | None:
        if any(type(item) is not int or item < 0 for item in value):
            return "actual_reps must contain only non-negative integers"
        return None

    def __post_init__(self):
        super().__post_init__()

        errors = []
        if self.is_completed and self.is_skipped:
            errors.append({
                "field": "is_skipped",
                "message": "exercise cannot be completed and skipped at the same time",
            })

        if len(self.actual_reps) != self.completed_sets:
            errors.append({
                "field": "actual_reps",
                "message": "actual_reps length must match completed_sets",
            })

        if errors:
            raise DTOValidationError(errors)

    def to_document(self) -> dict:
        return {item.name: getattr(self, item.name) for item in fields(self)}


@dataclass
class SessionFinishDTO(BaseDTO):
    exercises: list[SessionFinishExerciseDTO] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()

        validated = []
        errors = []

        for index, exercise in enumerate(self.exercises):
            if not isinstance(exercise, dict):
                errors.append({
                    "field": f"exercises.{index}",
                    "message": "must be an object",
                })
                continue

            try:
                validated.append(SessionFinishExerciseDTO.from_dict(exercise))
            except DTOValidationError as exc:
                for error in exc.errors:
                    errors.append({
                        "field": f"exercises.{index}.{error['field']}",
                        "message": error["message"],
                    })

        if errors:
            raise DTOValidationError(errors)

        self.exercises = validated

    def exercises_document(self) -> list[dict]:
        return [exercise.to_document() for exercise in self.exercises]

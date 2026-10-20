from app.repositories.program import ProgramRepository
from app.errors.program import ProgramNotFoundError, InvalidProgramIdError, ProgramAccessDeniedError
from app.dtos.utils import validate_object_id
from app.dtos.base import DTOValidationError
from bson import ObjectId


class ProgramService:
    def __init__(self, program_repo: ProgramRepository):
        self.program_repo = program_repo

    def create(self, data: dict, author_id: str) -> dict:
        self._validate_exercises(data["exercises"])
        return self.program_repo.create(data, author_id)

    def get_all(self, user_id: str) -> list[dict]:
        return self.program_repo.get_all(user_id)

    def get_by_id(self, program_id: str, user_id: str) -> dict:
        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise InvalidProgramIdError()

        program = self.program_repo.get_by_id(program_id)

        if program is None:
            raise ProgramNotFoundError()

        if not program["is_public"] and program["author_id"] != ObjectId(user_id):
            raise ProgramNotFoundError("Program not found")

        return program

    def update(self, program_id: str, data: dict, user_id: str) -> dict:
        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise InvalidProgramIdError()

        program = self.program_repo.get_by_id(program_id)
        if program is None:
            raise ProgramNotFoundError()

        if program["author_id"] != ObjectId(user_id):
            raise ProgramAccessDeniedError("You don't have access to update this program")

        if "exercises" in data:
            self._validate_exercises(data["exercises"])

        return self.program_repo.update(program_id, data)

    def delete(self, program_id: str, user_id: str) -> None:
        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise InvalidProgramIdError()

        program = self.program_repo.get_by_id(program_id)
        if program is None:
            raise ProgramNotFoundError()

        if program["author_id"] != ObjectId(user_id):
            raise ProgramAccessDeniedError("You don't have access to delete this program")

        self.program_repo.delete(program_id)

    def _validate_exercises(self, exercises: list) -> None:
        errors = []
        exercise_ids = []

        for idx, ex in enumerate(exercises):
            ex_id = ex["exercise_id"] if isinstance(ex, dict) else ex.exercise_id
            try:
                exercise_ids.append(ObjectId(ex_id))
            except Exception:
                errors.append({"field": f"exercises.{idx}.exercise_id", "message": "Invalid ID format"})

        if not errors:
            existing_ids = self.program_repo.get_existing_exercise_ids(exercise_ids)

            for idx, obj_id in enumerate(exercise_ids):
                if obj_id not in existing_ids:
                    errors.append({"field": f"exercises.{idx}.exercise_id", "message": "Exercise not found"})

        if errors:
            raise DTOValidationError(errors)
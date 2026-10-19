from app.repositories.program import ProgramRepository
from app.errors.base import AppError
from app.errors.user import AccessDeniedError
from app.dtos.utils import validate_object_id
from app.dtos.base import DTOValidationError
from bson import ObjectId
from app.database import get_db

class ProgramService:
    def __init__(self, program_repo: ProgramRepository):
        self.program_repo = program_repo

    def create(self, data: dict, author_id: str) -> dict:
        self._validate_exercises(data["exercises"])
        return self.program_repo.create(data, author_id)

    def get_all(self, user_id: str) -> list[dict]:
        return self.program_repo.get_all(user_id)

    def get_by_id(self, program_id: str, user_id: str) -> dict:
        from app.dtos.utils import validate_object_id
        from app.dtos.base import DTOValidationError
        from bson import ObjectId

        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise AppError("Invalid program ID")

        program = self.program_repo.get_by_id(program_id)

        if program is None:
            raise AppError("Program not found")

        if not program["is_public"] and program["author_id"] != ObjectId(user_id):
            raise AccessDeniedError("You don't have access to this program")

        return program

    def update(self, program_id: str, data: dict, user_id: str) -> dict:
        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise AppError("Invalid program ID")

        # 2. Ищем программу
        program = self.program_repo.get_by_id(program_id)
        if program is None:
            raise AppError("Program not found")

        if program["author_id"] != ObjectId(user_id):
            raise AccessDeniedError("You don't have access to update this program")

        self._validate_exercises(data["exercises"])
        return self.program_repo.update(program_id, data)

    def delete(self, program_id: str, user_id: str) -> None:
        try:
            validate_object_id(program_id, "id")
        except DTOValidationError:
            raise AppError("Invalid program ID")

        program = self.program_repo.get_by_id(program_id)
        if program is None:
            raise AppError("Program not found")

        # Проверка прав: удалять может только владелец
        if program["author_id"] != ObjectId(user_id):
            raise AccessDeniedError("You don't have access to delete this program")

        self.program_repo.delete(program_id)

    def _validate_exercises(self, exercises: list) -> None:
        db = get_db()
        errors = []

        for idx, ex in enumerate(exercises):
            # ex может быть словарем (из PUT) или объектом DTO (из POST)
            ex_id = ex["exercise_id"] if isinstance(ex, dict) else ex.exercise_id

            try:
                obj_id = ObjectId(ex_id)
            except Exception:
                errors.append({"field": f"exercises.{idx}.exercise_id", "message": "Invalid ID format"})
                continue

            if not db.exercises.find_one({"_id": obj_id}):
                errors.append({"field": f"exercises.{idx}.exercise_id", "message": "Exercise not found"})

        if errors:
            # Выбрасываем ошибку валидации, которую контроллер превратит в 400 BAD_REQUEST
            raise DTOValidationError(errors)
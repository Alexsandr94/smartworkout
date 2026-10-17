from collections.abc import Sequence

from bson import ObjectId

from app.common.pagination import Page, PaginationParams, paginate
from app.errors.exercises import ExerciseInUseError, ExerciseNotFoundError
from app.models.exercise import Exercise
from app.repositories.exercises import ExerciseRepository


class ExerciseService:
    def __init__(self, exercise_repo: ExerciseRepository):
        self.exercise_repo = exercise_repo

    def create(self, values: dict[str, object]) -> Exercise:
        return self.exercise_repo.create(values)

    def get(self, exercise_id: ObjectId) -> Exercise:
        exercise = self.exercise_repo.find_by_id(exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError()
        return exercise

    def update(self, exercise_id: ObjectId, changes: dict[str, object]) -> Exercise:
        exercise = self.exercise_repo.update(exercise_id, changes)
        if exercise is None:
            raise ExerciseNotFoundError()
        return exercise

    def delete(self, exercise_id: ObjectId) -> None:
        self.get(exercise_id)
        if self.exercise_repo.is_used_in_programs(exercise_id):
            raise ExerciseInUseError()
        if not self.exercise_repo.delete(exercise_id):
            raise ExerciseNotFoundError()

    def list(
        self, *, muscle_groups: Sequence[str] | None = None,
        equipment: Sequence[str] | None = None, search: str | None = None,
        pagination: PaginationParams = PaginationParams(),
    ) -> Page[Exercise]:
        exercises = self.exercise_repo.find_page(
            muscle_groups=muscle_groups, equipment=equipment, search=search, pagination=pagination,
        )
        return paginate(exercises, pagination, key=lambda exercise: exercise.id)

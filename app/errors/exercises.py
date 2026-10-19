from http import HTTPStatus

from app.errors.base import AppError


class ExerciseNotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = 'NOT_FOUND'

    def __init__(self, message: str = 'Exercise not found'):
        super().__init__(message)


class ExerciseInUseError(AppError):
    status = HTTPStatus.CONFLICT
    code = 'CONFLICT'

    def __init__(self, message: str = 'Exercise is used in one or more programs'):
        super().__init__(message)

from http import HTTPStatus

from app.errors.base import AppError


class InvalidProgramIdError(AppError):
    status = HTTPStatus.BAD_REQUEST
    code = "BAD_REQUEST"

    def __init__(self, message: str = "invalid program id format"):
        super().__init__(message)


class ProgramNotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"

    def __init__(self, message: str = "program not found"):
        super().__init__(message)


class AlreadyInFavoritesError(AppError):
    status = HTTPStatus.CONFLICT
    code = "CONFLICT"

    def __init__(self, message: str = "program already in favorites"):
        super().__init__(message)


class ProgramNotInFavoritesError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"

    def __init__(self, message: str = "program not found in favorites"):
        super().__init__(message)


class ForbiddenError(AppError):
    status = HTTPStatus.FORBIDDEN
    code = "FORBIDDEN"

    def __init__(self, message: str = "forbidden"):
        super().__init__(message)
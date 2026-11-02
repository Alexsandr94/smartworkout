from http import HTTPStatus

from app.errors.base import AppError


class SessionNotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"

    def __init__(self, message: str = "Session not found"):
        super().__init__(message)


class SessionProgramNotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"

    def __init__(self, message: str = "Program not found"):
        super().__init__(message)


class SessionAlreadyFinishedError(AppError):
    status = HTTPStatus.CONFLICT
    code = "CONFLICT"

    def __init__(self, message: str = "Session is already finished"):
        super().__init__(message)

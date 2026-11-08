from http import HTTPStatus
from app.errors.base import AppError

class ProgramNotFoundError(AppError):
    status = HTTPStatus.NOT_FOUND
    code = "NOT_FOUND"

    def __init__(self, message: str = "Program not found"):
        super().__init__(message)

class InvalidProgramIdError(AppError):
    status = HTTPStatus.BAD_REQUEST
    code = "BAD_REQUEST"

    def __init__(self, message: str = "Invalid program ID"):
        super().__init__(message)

class ProgramAccessDeniedError(AppError):
    status = HTTPStatus.FORBIDDEN
    code = "FORBIDDEN"

    def __init__(self, message: str = "You don't have access to this program"):
        super().__init__(message)
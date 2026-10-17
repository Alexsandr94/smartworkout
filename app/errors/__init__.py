from app.errors.base import AppError
from app.errors.exercises import ExerciseInUseError, ExerciseNotFoundError

from app.errors.auth import (
    AuthorizationRequiredError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
)

from app.errors.user import (
    AccessDeniedError,
    DuplicateEmailError,
    UserNotFoundError,
)

__all__ = [
    "AppError",
    "ExerciseInUseError",
    "ExerciseNotFoundError",
    "AuthorizationRequiredError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "AccessDeniedError",
    "DuplicateEmailError",
    "UserNotFoundError",
]

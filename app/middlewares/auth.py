from app.core.config import settings
from app.errors.auth import (
    AuthorizationRequiredError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.errors.user import AccessDeniedError
from app.security.token import verify


def require_auth(request, next_handler):
    header = request["headers"].get("Authorization", "")

    if not header.startswith("Bearer "):
        raise AuthorizationRequiredError()

    token = header.removeprefix("Bearer ").strip()

    try:
        payload = verify(token, settings.token_secret)
    except (TokenExpiredError, TokenInvalidError):
        raise AuthorizationRequiredError() from None

    request["user"] = {
        "id": payload["sub"],
        "email": payload.get("email"),
        "role": payload.get("role"),
    }

    return next_handler(request)


def require_admin(request, next_handler):
    user = request.get("user")

    if not user:
        raise AuthorizationRequiredError()

    if user.get("role") != "ADMIN":
        raise AccessDeniedError()

    return next_handler(request)
from app.core.config import settings
from app.errors.auth import InvalidCredentialsError
from app.security.password import hash_password, verify_password
from app.security.token import issue, verify
from app.services.user.service import UserService

_DUMMY_HASH = hash_password("dummy")

class AuthService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def register(self, email: str, password: str) -> dict:
        password_hash = hash_password(password)
        return self.user_service.create(email, password_hash)

    @staticmethod
    def _issue_tokens(payload: dict) -> dict:
        return {
            "access_token": issue(
                payload,
                settings.token_secret,
                settings.access_ttl_seconds,
                "access",
            ),
            "refresh_token": issue(
                payload,
                settings.token_secret,
                settings.refresh_ttl_seconds,
                "refresh",
            ),
            "refresh_ttl": settings.refresh_ttl_seconds,
        }

    def login(self, email: str, password: str) -> dict:
        user = self.user_service.find_by_email(email)
        password_hash = user["password_hash"] if user else _DUMMY_HASH

        password_ok = verify_password(password, password_hash)

        if not user or not password_ok:
            raise InvalidCredentialsError()

        payload = {
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
        }

        return {
            **self._issue_tokens(payload),
            "user": user,
        }

    def refresh(self, refresh_token: str) -> dict:
        payload = verify(
            refresh_token,
            settings.token_secret,
            "refresh",
        )

        return self._issue_tokens({
            "sub": payload["sub"],
            "email": payload["email"],
            "role": payload["role"],
        })
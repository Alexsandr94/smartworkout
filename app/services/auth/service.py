from app.core.config import settings
from app.errors.auth import InvalidCredentialsError
from app.models.auth import AuthTokens, LoginResult
from app.models.user import User
from app.security.password import hash_password, verify_password
from app.security.token import issue, verify
from app.services.user.service import UserService


_DUMMY_HASH = hash_password("dummy")


class AuthService:
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def register(self, email: str, password: str) -> User:
        password_hash = hash_password(password)
        return self.user_service.create(email, password_hash)

    @staticmethod
    def _issue_tokens(payload: dict) -> AuthTokens:
        return AuthTokens(
            access_token=issue(
                payload,
                settings.token_secret,
                settings.access_ttl_seconds,
                "access",
            ),
            refresh_token=issue(
                payload,
                settings.token_secret,
                settings.refresh_ttl_seconds,
                "refresh",
            ),
            refresh_ttl=settings.refresh_ttl_seconds,
        )

    def login(self, email: str, password: str) -> LoginResult:
        user = self.user_service.find_by_email(email)

        password_hash = (
            user.password_hash if user is not None else _DUMMY_HASH
        )

        password_ok = verify_password(password, password_hash)

        if user is None or not password_ok:
            raise InvalidCredentialsError()

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }

        return LoginResult(
            user=user,
            tokens=self._issue_tokens(payload),
        )

    def refresh(self, refresh_token: str) -> AuthTokens:
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
from dataclasses import dataclass, field

from app.models.user import User


@dataclass(frozen=True)
class AuthTokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    refresh_ttl: int


@dataclass(frozen=True)
class LoginResult:
    user: User
    tokens: AuthTokens = field(repr=False)
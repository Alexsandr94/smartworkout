from unittest.mock import MagicMock

import pytest
from bson import ObjectId

from app.core.config import settings
from app.errors.auth import InvalidCredentialsError, TokenExpiredError, TokenInvalidError
from app.errors.user import DuplicateEmailError
from app.security.password import verify_password, hash_password
from app.security.token import issue, verify
from app.services.auth.service import AuthService

from datetime import UTC, datetime

from bson import ObjectId
from app.models.user import User
from app.models.auth import AuthTokens, LoginResult
from app.security.token import verify
from app.core.config import settings


EMAIL = "student@example.test"
PASSWORD = "secure_password_123"

@pytest.fixture
def user():
    return User(
        id=ObjectId(),
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        role="USER",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def user_service():
    return MagicMock()


@pytest.fixture
def service(user_service):
    return AuthService(user_service)


from app.models.user import User


def test_register_hashes_password_and_delegates_to_user_service(
    service, user_service, user
):
    user_service.create.return_value = user

    result = service.register(EMAIL, PASSWORD)

    assert isinstance(result, User)
    assert result is user
    assert result.role == "USER"

    user_service.create.assert_called_once()

    args = user_service.create.call_args.args

    assert args[0] == EMAIL
    assert args[1] != PASSWORD
    assert verify_password(PASSWORD, args[1])

    assert not hasattr(result, "access_token")
    assert not hasattr(result, "refresh_token")


def test_register_propagates_duplicate_email(service, user_service):
    user_service.create.side_effect = DuplicateEmailError()
    with pytest.raises(DuplicateEmailError):
        service.register(EMAIL, PASSWORD)


def test_login_returns_valid_access_refresh_and_user(
    service, user_service, user
):
    user_service.find_by_email.return_value = user

    result = service.login(EMAIL, PASSWORD)

    assert isinstance(result, LoginResult)
    assert result.user is user
    assert isinstance(result.tokens, AuthTokens)

    access_payload = verify(
        result.tokens.access_token,
        settings.token_secret,
        "access",
    )

    refresh_payload = verify(
        result.tokens.refresh_token,
        settings.token_secret,
        "refresh",
    )

    assert access_payload["sub"] == str(user.id)
    assert access_payload["email"] == user.email
    assert access_payload["role"] == user.role

    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"

    assert result.tokens.refresh_ttl == settings.refresh_ttl_seconds


@pytest.mark.parametrize("user_exists", [False, True])
def test_login_rejects_unknown_user_or_wrong_password(
    service, user_service, user_exists, user
):
    user_service.find_by_email.return_value = (
        user if user_exists else None
    )

    with pytest.raises(InvalidCredentialsError):
        service.login(
            EMAIL,
            "wrong_password" if user_exists else PASSWORD,
        )


def test_refresh_issues_access_and_refresh_without_db_lookup(
    service, user_service, user
):
    original = issue(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        },
        settings.token_secret,
        300,
        "refresh",
    )

    result = service.refresh(original)

    assert isinstance(result, AuthTokens)
    assert result.refresh_ttl == settings.refresh_ttl_seconds

    access_payload = verify(
        result.access_token,
        settings.token_secret,
        "access",
    )

    refresh_payload = verify(
        result.refresh_token,
        settings.token_secret,
        "refresh",
    )

    assert access_payload["sub"] == str(user.id)
    assert access_payload["role"] == user.role

    assert refresh_payload["sub"] == str(user.id)
    assert refresh_payload["type"] == "refresh"

    user_service.find_by_email.assert_not_called()


def test_refresh_rejects_access_token(service):
    token = issue({"sub": "123", "email": EMAIL, "role": "USER"},
                  settings.token_secret, 300, "access")
    with pytest.raises(TokenInvalidError):
        service.refresh(token)


def test_refresh_rejects_expired_token(service):
    token = issue({"sub": "123", "email": EMAIL, "role": "USER"},
                  settings.token_secret, -1, "refresh")
    with pytest.raises(TokenExpiredError):
        service.refresh(token)


def test_refresh_rejects_forged_token(service):
    token = issue({"sub": "123", "email": EMAIL, "role": "USER"},
                  "other-secret", 300, "refresh")
    with pytest.raises(TokenInvalidError):
        service.refresh(token)

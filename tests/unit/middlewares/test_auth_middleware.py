"""Bearer-auth and role middleware."""

import pytest

from app.core.config import settings
from app.errors.auth import AuthorizationRequiredError
from app.errors.user import AccessDeniedError
from app.middlewares.auth import require_admin, require_auth
from app.security.token import issue


PAYLOAD = {
    "sub": "507f1f77bcf86cd799439011",
    "email": "student@example.test",
    "role": "USER",
}


def request_with_token(token):
    return {"headers": {"Authorization": "Bearer " + token}}


def test_require_auth_sets_request_user_and_calls_handler():
    token = issue(PAYLOAD, settings.token_secret, 300, "access")
    request = request_with_token(token)
    result = require_auth(request, lambda req: req["user"].copy())
    assert result == {"id": PAYLOAD["sub"], "email": PAYLOAD["email"], "role": "USER"}
    assert request["user"] == result


@pytest.mark.parametrize("header", [None, "", "access-token", "Basic example", "Bearer "])
def test_require_auth_rejects_missing_or_bad_header(header):
    request = {"headers": {} if header is None else {"Authorization": header}}
    with pytest.raises(AuthorizationRequiredError):
        require_auth(request, lambda _: pytest.fail("handler should not run"))


def test_require_auth_rejects_refresh_token():
    token = issue(PAYLOAD, settings.token_secret, 300, "refresh")
    with pytest.raises(AuthorizationRequiredError):
        require_auth(request_with_token(token), lambda _: pytest.fail("handler should not run"))


def test_require_auth_rejects_expired_access_token():
    token = issue(PAYLOAD, settings.token_secret, -1, "access")
    with pytest.raises(AuthorizationRequiredError):
        require_auth(request_with_token(token), lambda _: pytest.fail("handler should not run"))


def test_require_admin_allows_admin():
    request = {"user": {"role": "ADMIN"}}
    assert require_admin(request, lambda _: "passed") == "passed"


def test_require_admin_rejects_user_and_anonymous():
    with pytest.raises(AccessDeniedError):
        require_admin({"user": {"role": "USER"}}, lambda _: None)
    with pytest.raises(AuthorizationRequiredError):
        require_admin({}, lambda _: None)

"""Custom HMAC token: access/refresh separation, integrity and expiry."""

import pytest

from app.errors.auth import TokenExpiredError, TokenInvalidError
from app.security.token import issue, verify


SECRET = "test-secret-that-is-not-used-in-production"
PAYLOAD = {"sub": "507f1f77bcf86cd799439011", "email": "student@example.test", "role": "USER"}


@pytest.mark.parametrize("token_type", ["access", "refresh"])
def test_issue_and_verify_preserves_claims_and_type(token_type):
    token = issue(PAYLOAD, SECRET, 300, token_type)
    verified = verify(token, SECRET, token_type)
    assert all(verified[name] == value for name, value in PAYLOAD.items())
    assert verified["type"] == token_type
    assert type(verified["exp"]) is int
    assert len(token.split(".")) == 2


def test_access_token_cannot_be_used_as_refresh_and_vice_versa():
    for issued_as, checked_as in (("access", "refresh"), ("refresh", "access")):
        token = issue(PAYLOAD, SECRET, 300, issued_as)
        with pytest.raises(TokenInvalidError):
            verify(token, SECRET, checked_as)


def test_verify_rejects_wrong_secret_and_tampered_signature():
    token = issue(PAYLOAD, SECRET, 300, "refresh")
    with pytest.raises(TokenInvalidError):
        verify(token, "different-secret", "refresh")

    payload, signature = token.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    corrupted = payload + "." + replacement + signature[1:]
    with pytest.raises(TokenInvalidError):
        verify(corrupted, SECRET, "refresh")


@pytest.mark.parametrize("raw", ["", "abc", "a.b.c", "abc.def", None])
def test_verify_rejects_malformed_tokens(raw):
    with pytest.raises(TokenInvalidError):
        verify(raw, SECRET, "refresh")


def test_expired_token_is_rejected():
    token = issue(PAYLOAD, SECRET, -1, "refresh")
    with pytest.raises(TokenExpiredError):
        verify(token, SECRET, "refresh")


def test_user_payload_cannot_override_token_type_or_expiration():
    token = issue({**PAYLOAD, "type": "refresh", "exp": 0}, SECRET, 300, "access")
    result = verify(token, SECRET, "access")
    assert result["type"] == "access"
    assert result["exp"] > 0

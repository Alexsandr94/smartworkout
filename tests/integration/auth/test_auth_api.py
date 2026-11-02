"""Full-stack HTTP tests for the four auth endpoints.

Uses existing tests/conftest.py `api` fixture (temporary MongoDB + HTTP server).
This file targets the handlers provided in chat, not the older main branch.
"""

import json
from http.client import HTTPConnection
from http.cookies import SimpleCookie

import pytest
from bson import ObjectId

from app.core.config import settings
from app.security.password import verify_password
from app.security.token import issue, verify


EMAIL = "student-auth@example.test"
PASSWORD = "correct_password_123"


def _cookie(headers):
    assert "Set-Cookie" in headers
    parsed = SimpleCookie()
    parsed.load(headers["Set-Cookie"])
    assert "refresh_token" in parsed
    return parsed["refresh_token"]


def _post_with_refresh_cookie(api, path, refresh_token):
    """The shared api.request() does not accept arbitrary Cookie headers."""
    connection = HTTPConnection("127.0.0.1", api.port, timeout=5)
    try:
        connection.request(
            "POST", path,
            headers={"Cookie": f"refresh_token={refresh_token}"},
        )
        response = connection.getresponse()
        raw = response.read()
        return response.status, (json.loads(raw) if raw else None), dict(response.getheaders())
    finally:
        connection.close()


class TestAuthAPI:
    @pytest.fixture(autouse=True)
    def setup(self, api):
        self.api = api
        self.users = api.fixture.db.users

    def register(self, email=EMAIL, password=PASSWORD):
        return self.api.request(
            "POST", "/auth/register", role=None,
            payload={"email": email, "password": password},
        )

    def login(self, email=EMAIL, password=PASSWORD):
        return self.api.request(
            "POST", "/auth/login", role=None,
            payload={"email": email, "password": password},
        )

    def test_register_creates_user_but_does_not_log_in(self):
        status, body, headers = self.register(" STUDENT-AUTH@EXAMPLE.TEST ")
        assert status == 201
        assert set(body) == {"id", "email", "role"}
        assert body["role"] == "USER"
        assert ObjectId.is_valid(body["id"])
        assert body["email"] == EMAIL
        assert "Set-Cookie" not in headers

        stored = self.users.find_one({"_id": ObjectId(body["id"])})
        assert stored is not None
        assert stored["role"] == "USER"
        assert stored["email"] == EMAIL
        assert stored["password_hash"] != PASSWORD
        assert verify_password(PASSWORD, stored["password_hash"])

    def test_register_duplicate_email_returns_conflict(self):
        assert self.register()[0] == 201
        status, body, _ = self.register("STUDENT-AUTH@example.test")
        assert status == 409
        assert body["code"] == "DUPLICATE_EMAIL"
        assert self.users.count_documents({}) == 1

    @pytest.mark.parametrize("payload,field", [
        ({}, "email"),
        ({"email": EMAIL}, "password"),
        ({"password": PASSWORD}, "email"),
        ({"email": "invalid", "password": PASSWORD}, "email"),
        ({"email": EMAIL, "password": "12345"}, "password"),
        ({"email": EMAIL, "password": "x" * 33}, "password"),
        ({"email": EMAIL, "password": None}, "password"),
        ({"email": EMAIL, "password": PASSWORD, "role": "ADMIN"}, "role"),
    ])
    def test_register_validation_returns_400(self, payload, field):
        status, body, _ = self.api.request("POST", "/auth/register", role=None, payload=payload)
        assert status == 400
        assert body["code"] == "BAD_REQUEST"
        assert body["message"] == "Validation failed"
        assert field in {item["field"] for item in body["errors"]}
        assert self.users.count_documents({}) == 0

    @pytest.mark.parametrize("payload", [None, [], "not an object"])
    def test_register_rejects_nonobject_json_body(self, payload):
        status, body, _ = self.api.request("POST", "/auth/register", role=None, payload=payload)
        assert status == 400
        assert body["errors"][0]["field"] == "body"

    def test_login_returns_access_token_user_and_refresh_cookie(self):
        _, registered, _ = self.register()
        status, body, headers = self.login("STUDENT-AUTH@EXAMPLE.TEST")
        assert status == 200
        assert set(body) == {"access_token", "user"}
        assert body["user"] == {"id": registered["id"], "email": EMAIL, "role": "USER"}
        assert "refresh_token" not in body

        access_payload = verify(body["access_token"], settings.token_secret, "access")
        assert access_payload["sub"] == registered["id"]
        assert access_payload["email"] == EMAIL
        assert access_payload["role"] == "USER"

        refresh = _cookie(headers)
        assert refresh["path"] == "/auth"
        assert refresh["httponly"]
        assert refresh["samesite"] == "Strict"
        assert bool(refresh["secure"]) == settings.is_production()
        assert int(refresh["max-age"]) == settings.refresh_ttl_seconds
        assert verify(refresh.value, settings.token_secret, "refresh")["sub"] == registered["id"]

    @pytest.mark.parametrize("email,password", [
        ("missing@example.test", PASSWORD),
        (EMAIL, "wrong_password"),
    ])
    def test_login_rejects_invalid_credentials(self, email, password):
        assert self.register()[0] == 201
        status, body, headers = self.login(email, password)
        assert status == 401
        assert body["code"] == "INVALID_CREDENTIALS"
        assert "Set-Cookie" not in headers

    @pytest.mark.parametrize("payload,field", [
        ({}, "email"),
        ({"email": EMAIL}, "password"),
        ({"email": "  ", "password": PASSWORD}, "email"),
        ({"email": EMAIL, "password": ""}, "password"),
        ({"email": EMAIL, "password": 123}, "password"),
    ])
    def test_login_validation_returns_400(self, payload, field):
        status, body, _ = self.api.request("POST", "/auth/login", role=None, payload=payload)
        assert status == 400
        assert body["code"] == "BAD_REQUEST"
        assert field in {item["field"] for item in body["errors"]}

    def test_login_password_keeps_whitespace(self):
        secret = "  custom-password  "
        assert self.register(password=secret)[0] == 201
        assert self.login(password=secret)[0] == 200
        assert self.login(password=secret.strip())[0] == 401

    def test_refresh_requires_cookie(self):
        status, body, _ = self.api.request("POST", "/auth/refresh", role=None)
        assert status == 401
        assert body == {"code": "UNAUTHORIZED", "message": "refresh token is required"}

    def test_refresh_returns_access_token_and_sets_refresh_cookie(self):
        _, registered, _ = self.register()
        _, _, login_headers = self.login()
        old_refresh = _cookie(login_headers).value
        status, body, headers = _post_with_refresh_cookie(self.api, "/auth/refresh", old_refresh)
        assert status == 200
        assert set(body) == {"access_token"}
        assert verify(body["access_token"], settings.token_secret, "access")["sub"] == registered["id"]
        refreshed = _cookie(headers)
        assert int(refreshed["max-age"]) == settings.refresh_ttl_seconds
        assert verify(refreshed.value, settings.token_secret, "refresh")["sub"] == registered["id"]
        # Tokens may be identical when issued during the same second.

    def test_refresh_rejects_access_token_as_refresh_cookie(self):
        self.register()
        _, login_body, _ = self.login()
        status, body, _ = _post_with_refresh_cookie(self.api, "/auth/refresh", login_body["access_token"])
        assert status == 401
        assert body["code"] == "TOKEN_INVALID"

    def test_refresh_rejects_invalid_signature(self):
        token = issue({"sub": str(ObjectId()), "email": EMAIL, "role": "USER"},
                      "invalid-secret", 300, "refresh")
        status, body, _ = _post_with_refresh_cookie(self.api, "/auth/refresh", token)
        assert status == 401
        assert body["code"] == "TOKEN_INVALID"

    def test_refresh_rejects_expired_token(self):
        expired = issue({"sub": str(ObjectId()), "email": EMAIL, "role": "USER"},
                        settings.token_secret, -1, "refresh")
        status, body, _ = _post_with_refresh_cookie(self.api, "/auth/refresh", expired)
        assert status == 401
        assert body["code"] == "TOKEN_EXPIRED"

    @pytest.mark.parametrize("with_cookie", [False, True])
    def test_logout_without_authorization_always_clears_cookie(self, with_cookie):
        if with_cookie:
            status, body, headers = _post_with_refresh_cookie(self.api, "/auth/logout", "invalid-token")
        else:
            status, body, headers = self.api.request("POST", "/auth/logout", role=None)
        assert status == 204
        assert body is None
        cleared = _cookie(headers)
        assert cleared.value == ""
        assert cleared["path"] == "/auth"
        assert cleared["httponly"]
        assert int(cleared["max-age"]) == 0

    def test_logout_is_idempotent(self):
        for _ in range(2):
            status, body, headers = self.api.request("POST", "/auth/logout", role=None)
            assert status == 204
            assert body is None
            assert int(_cookie(headers)["max-age"]) == 0

from http.cookies import SimpleCookie
from types import SimpleNamespace

import pytest

from app.core import cookies


def _morsel(header):
    parsed = SimpleCookie()
    parsed.load(header)
    return parsed["refresh_token"]


@pytest.mark.parametrize("production", [False, True])
def test_refresh_cookie_security_flags(monkeypatch, production):
    monkeypatch.setattr(cookies, "settings", SimpleNamespace(is_production=lambda: production))
    morsel = _morsel(cookies.build_refresh_cookie("token.value", 3600))
    assert morsel.value == "token.value"
    assert morsel["path"] == "/auth"
    assert morsel["httponly"]
    assert morsel["samesite"] == "Strict"
    assert bool(morsel["secure"]) is production
    assert morsel["max-age"] == "3600"


def test_clear_cookie_uses_same_name_and_path():
    morsel = _morsel(cookies.clear_refresh_cookie())
    assert morsel.value == ""
    assert morsel["max-age"] == "0"
    assert morsel["path"] == "/auth"
    assert morsel["httponly"]


def test_parse_cookies_reads_refresh_and_other_values():
    header = "refresh_token=token.value; theme=dark"
    assert cookies.parse_cookies(header) == {"refresh_token": "token.value", "theme": "dark"}


@pytest.mark.parametrize("header", [None, "", "not a valid cookie header"])
def test_parse_cookies_handles_missing_or_malformed_header(header):
    assert cookies.parse_cookies(header) == {}

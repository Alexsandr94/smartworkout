from http.cookies import CookieError, SimpleCookie

from app.core.config import settings

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/auth"


def parse_cookies(header: str | None) -> dict[str, str]:
    if not header:
        return {}

    cookie = SimpleCookie()

    try:
        cookie.load(header)
    except CookieError:
        return {}

    return {name: morsel.value for name, morsel in cookie.items()}


def build_refresh_cookie(token: str, max_age: int) -> str:
    cookie = SimpleCookie()
    cookie[REFRESH_COOKIE_NAME] = token

    morsel = cookie[REFRESH_COOKIE_NAME]
    morsel["max-age"] = max_age
    morsel["path"] = REFRESH_COOKIE_PATH
    morsel["httponly"] = True
    morsel["secure"] = settings.is_production()
    morsel["samesite"] = "Strict"

    return cookie.output(header="").strip()


def clear_refresh_cookie() -> str:
    return build_refresh_cookie("", 0)
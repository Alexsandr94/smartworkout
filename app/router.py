
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Callable

_PARAM_RE = re.compile(r"\{(\w+)\}")

Request = dict[str, Any]
Handler = Callable[[Request], Any]
Middleware = Callable[[Request, Handler], Any]


def _compile_pattern(pattern: str) -> re.Pattern:
    parts = _PARAM_RE.split(pattern)
    out = []

    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(f"(?P<{part}>[^/]+)")
        else:
            out.append(re.escape(part))

    return re.compile("^" + "".join(out) + "$")


@dataclass
class Route:
    method: str
    pattern: str
    handler: Handler
    regex: re.Pattern = field(init=False)

    def __post_init__(self):
        self.method = self.method.upper()
        self.regex = _compile_pattern(self.pattern)

@dataclass
class Router:
    routes: list[Route] = field(default_factory=list)
    global_middlewares: list[Middleware] = field(default_factory=list)

    def use(self, middleware: Middleware) -> Middleware:
        self.global_middlewares.append(middleware)
        return middleware

    @staticmethod
    def _wrap(middleware: Middleware, next_handler: Handler) -> Handler:
        def wrapped(request: Request):
            return middleware(request, next_handler)
        return wrapped

    def _register(
        self,
        method: str,
        path: str,
        middlewares: Iterable[Middleware] | None = None,
    ):
        def decorator(handler: Handler) -> Handler:
            all_mw = self.global_middlewares + list(middlewares or [])
            wrapped_handler: Handler = handler

            for mw in reversed(all_mw):
                wrapped_handler = self._wrap(mw, wrapped_handler)

            self.routes.append(Route(method, path, wrapped_handler))
            return handler
        return decorator

    def resolve(self, method: str, path: str) -> tuple[Route | None, dict, bool]:
        allowed = False

        for route in self.routes:
            match = route.regex.match(path)
            if match is None:
                continue

            allowed = True
            if route.method == method:
                return route, match.groupdict(), True
        return None, {}, allowed

    def get(self, path: str, middlewares: Iterable[Middleware] | None = None):
        return self._register("GET", path, middlewares)

    def post(self, path: str, middlewares: Iterable[Middleware] | None = None):
        return self._register("POST", path, middlewares)

    def put(self, path: str, middlewares: Iterable[Middleware] | None = None):
        return self._register("PUT", path, middlewares)

    def patch(self, path: str, middlewares: Iterable[Middleware] | None = None):
        return self._register("PATCH", path, middlewares)

    def delete(self, path: str, middlewares: Iterable[Middleware] | None = None):
        return self._register("DELETE", path, middlewares)
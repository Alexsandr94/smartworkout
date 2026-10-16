import json
import logging
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app.core.cookies import parse_cookies
from app.handlers import register_routes
from app.httpresponse import Response, error_response
from app.routing import router


MAX_BODY_SIZE = 1 * 1024 * 1024

log = logging.getLogger(__name__)


class HTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self) -> None:
        self._dispatch()

    def _read_body(self):
        length = int(
            self.headers.get("Content-Length") or 0
        )

        if length > MAX_BODY_SIZE:
            return None, error_response(
                {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "request body too large",
                },
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )

        if length == 0:
            return None, None

        try:
            body = json.loads(
                self.rfile.read(length)
            )
        except json.JSONDecodeError:
            return None, error_response(
                {
                    "code": "BAD_REQUEST",
                    "message": "invalid json body",
                },
                HTTPStatus.BAD_REQUEST,
            )

        return body, None

    def _dispatch(self) -> int:
        parsed = urlparse(self.path)

        path = parsed.path

        query = {
            key: value[0]
            for key, value in parse_qs(
                parsed.query
            ).items()
        }

        route, params, allowed = router.resolve(
            self.command,
            path,
        )

        if route is None:
            if allowed:
                payload = {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": "method not allowed",
                }
                status = HTTPStatus.METHOD_NOT_ALLOWED
            else:
                payload = {
                    "code": "NOT_FOUND",
                    "message": "not found",
                }
                status = HTTPStatus.NOT_FOUND

            response = error_response(payload, status)

            self._send(response)
            return int(response.status)

        body, err = self._read_body()

        if err is not None:
            if err.status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE:
                self.close_connection = True

            self._send(err)
            return int(err.status)

        
        request = {
            "method": self.command,
            "path": path,
            "params": params,
            "query": query,
            "headers": dict(self.headers),
            "cookies": parse_cookies(
                self.headers.get("Cookie")
            ),
            "body": body,
        }

        result = route.handler(request)
        self._send(result)
        return int(result.status)

    def _send(self, response: Response) -> None:
        if response.status == HTTPStatus.NO_CONTENT:
            self.send_response(response.status)
            for name, value in response.headers:
                self.send_header(name, value)
            self.end_headers()
            return
         
        payload = json.dumps(
            response.body
            if response.body is not None
            else {},
            ensure_ascii=False,
        ).encode("utf-8")

        self.send_response(response.status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )

        self.send_header("Content-Length", str(len(payload)))

        for name, value in response.headers:
            self.send_header(name, value)

        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_PATCH = _handle
    do_DELETE = _handle


def run(port: int = 8000) -> None:
    register_routes()

    httpd = ThreadingHTTPServer(("", port), HTTPRequestHandler)
    log.info("Starting HTTP server on port %d",port)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("stopping server")
        httpd.server_close()
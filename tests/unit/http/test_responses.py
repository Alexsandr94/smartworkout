from http import HTTPStatus
import io
import json

from app.httpresponse import Response
from app.server import HTTPRequestHandler



class ResponseCapture:

    def __init__(self):
        self.wfile = io.BytesIO()
        self.headers = {}
        self.status = None

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.headers[name] = value

    def end_headers(self):
        pass


def test_204_has_no_body_or_content_length():
    capture = ResponseCapture()
    HTTPRequestHandler._send(capture, Response(HTTPStatus.NO_CONTENT, headers=[('X-Request-Id', 'request-test')]))
    assert capture.status == 204
    assert capture.wfile.getvalue() == b''
    assert capture.headers.get('X-Request-Id') == 'request-test'
    assert 'Content-Length' not in capture.headers
    assert 'Content-Type' not in capture.headers


def test_json_responses_unchanged():
    for status, body in ((200, {'message': 'Привет'}), (400, {'code': 'BAD_REQUEST', 'message': 'Validation failed'}), (200, None)):
        capture = ResponseCapture()
        HTTPRequestHandler._send(capture, Response(status, body))
        raw = capture.wfile.getvalue()
        assert capture.status == status
        assert json.loads(raw) == (body if body is not None else {})
        assert capture.headers.get('Content-Length') == str(len(raw))
        assert capture.headers.get('Content-Type') == 'application/json; charset=utf-8'

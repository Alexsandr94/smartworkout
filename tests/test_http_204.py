import io
import json
import socket
import unittest
from http import HTTPStatus

from app.httpresponse import Response
from app.repositories.exercises import ExerciseRepository
from app.server import HTTPRequestHandler
from tests.exercises_support import TemporaryAPIServer


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


class HTTPResponseTests(unittest.TestCase):
    def test_204_has_no_body_or_content_length(self):
        capture = ResponseCapture()
        HTTPRequestHandler._send(capture, Response(HTTPStatus.NO_CONTENT, headers=[('X-Request-Id', 'request-test')]))
        self.assertEqual(capture.status, 204)
        self.assertEqual(capture.wfile.getvalue(), b'')
        self.assertEqual(capture.headers.get('X-Request-Id'), 'request-test')
        self.assertNotIn('Content-Length', capture.headers)
        self.assertNotIn('Content-Type', capture.headers)

    def test_json_responses_unchanged(self):
        for status, body in ((200, {'message': 'Привет'}), (400, {'code': 'BAD_REQUEST', 'message': 'Validation failed'}), (200, None)):
            with self.subTest(status=status, body=body):
                capture = ResponseCapture()
                HTTPRequestHandler._send(capture, Response(status, body))
                raw = capture.wfile.getvalue()
                self.assertEqual(capture.status, status)
                self.assertEqual(json.loads(raw), body if body is not None else {})
                self.assertEqual(capture.headers.get('Content-Length'), str(len(raw)))
                self.assertEqual(capture.headers.get('Content-Type'), 'application/json; charset=utf-8')

    def test_keepalive_after_delete(self):
        api = TemporaryAPIServer()
        self.addCleanup(api.close)
        doc = ExerciseRepository(api.fixture.db).create({'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT']})
        token = api.tokens.get('ADMIN')
        with socket.create_connection(('127.0.0.1', api.port), timeout=5) as connection, connection.makefile('rb') as wire:
            def request(method, path):
                raw = f'{method} {path} HTTP/1.1\r\nHost: localhost\r\nAuthorization: Bearer {token}\r\n\r\n'
                connection.sendall(raw.encode('ascii'))
                status_line = wire.readline().strip()
                headers = {}
                while True:
                    line = wire.readline()
                    if line in (b'\r\n', b''):
                        break
                    name, value = line.decode('ascii').split(':', 1)
                    headers[name.lower()] = value.strip()
                return status_line, headers

            first_status, first_headers = request('DELETE', '/exercises/' + str(doc.id))
            self.assertTrue(first_status.startswith(b'HTTP/1.1 204 '), first_status)
            next_status, next_headers = request('GET', '/exercises')
            self.assertTrue(next_status.startswith(b'HTTP/1.1 200 '), next_status)
            body = json.loads(wire.read(int(next_headers.get('content-length'))))
            self.assertEqual(body.get('data'), [])
            self.assertNotIn('content-length', first_headers)
            self.assertTrue(first_headers.get('x-request-id'))


if __name__ == '__main__':
    unittest.main()

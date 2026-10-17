import json
import socket

from app.repositories.exercises import ExerciseRepository



class TestHTTPConnections:

    def test_keepalive_after_delete(self, api):
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
                return (status_line, headers)
            first_status, first_headers = request('DELETE', '/exercises/' + str(doc.id))
            assert first_status.startswith(b'HTTP/1.1 204 '), first_status
            next_status, next_headers = request('GET', '/exercises')
            assert next_status.startswith(b'HTTP/1.1 200 '), next_status
            body = json.loads(wire.read(int(next_headers.get('content-length'))))
            assert body.get('data') == []
            assert 'content-length' not in first_headers
            assert first_headers.get('x-request-id')

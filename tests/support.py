from contextlib import ExitStack
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
from uuid import uuid4
import importlib
import json
import sys

from pymongo import MongoClient
from pytest import MonkeyPatch

from app.core.config import settings



class TemporaryDatabase:
    prefix = 'smartworkout_exercises_test_'

    def __init__(self):
        self.name = self.prefix + uuid4().hex
        self.client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000, tz_aware=True)
        try:
            self.client.admin.command('ping')
        except Exception:
            self.client.close()
            raise
        self.db = self.client[self.name]

    def close(self):
        if not self.name.startswith(self.prefix) or self.name == settings.mongo_db:
            raise RuntimeError('Refusing to drop a non-test database')
        try:
            self.client.drop_database(self.name)
        finally:
            self.client.close()


NO_BODY = object()



class TemporaryAPIServer:
    def __init__(self):
        from app.database import client, indexes, validators
        from app.handlers import register_routes
        from app.routing import router
        from app.security.token import issue
        from app.server import HTTPRequestHandler

        self.fixture = TemporaryDatabase()
        self.context = ExitStack()
        self.context.callback(self.fixture.close)
        try:
            patcher = self.context.enter_context(MonkeyPatch.context())
            patcher.setattr(client, '_db', self.fixture.db)
            validators.ensure_schema()
            indexes.ensure_indexes()
            was_loaded = 'app.dependencies' in sys.modules
            dependencies = importlib.import_module('app.dependencies')
            if was_loaded:
                importlib.reload(dependencies)
            original_routes = list(router.routes)
            self.context.callback(lambda: router.routes.__setitem__(slice(None), original_routes))
            router.routes.clear()
            for module_name in ('app.handlers.auth', 'app.handlers.exercises', 'app.handlers.program', 'app.handlers.favorites'):
                if module_name in sys.modules:
                    importlib.reload(sys.modules.get(module_name))
            register_routes()
            self.server = ThreadingHTTPServer(('127.0.0.1', 0), HTTPRequestHandler)
            self.context.callback(self.server.server_close)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.context.callback(self.thread.join, 3)
            self.context.callback(self.server.shutdown)
            self.port = self.server.server_port
            self.tokens = {role: issue({'sub': '507f1f77bcf86cd799439011', 'email': 'test@example.test', 'role': role}, settings.token_secret, 300) for role in ('USER', 'ADMIN')}
        except Exception:
            self.context.close()
            raise

    def request(self, method, path, role='ADMIN', payload=NO_BODY):
        headers = {}
        if role is not None:
            headers['Authorization'] = 'Bearer ' + self.tokens.get(role)
        body = None
        if payload is not NO_BODY:
            body = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        connection = HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, json.loads(raw) if raw else None, dict(response.getheaders())
        finally:
            connection.close()

    def close(self):
        self.context.close()

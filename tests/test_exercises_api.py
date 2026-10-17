import unittest
from datetime import UTC, datetime
from urllib.parse import urlencode

from bson import ObjectId

from app.repositories.exercises import ExerciseRepository
from tests.exercises_support import TemporaryAPIServer


class ExerciseAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = TemporaryAPIServer()
        cls.addClassCleanup(cls.api.close)
        cls.db = cls.api.fixture.db

    def setUp(self):
        for name in ('exercises', 'programs', 'users'):
            self.db[name].delete_many({})
        self.repo = ExerciseRepository(self.db)

    @staticmethod
    def values(**changes):
        return {'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT'], **changes}

    def seed(self, **changes):
        return self.repo.create(self.values(**changes))

    def test_reads_require_authorization(self):
        for path in ('/exercises', '/exercises/507f1f77bcf86cd799439011'):
            with self.subTest(path=path):
                status, body, headers = self.api.request('GET', path, role=None)
                self.assertEqual(status, 401)
                self.assertEqual(body.get('code'), 'UNAUTHORIZED')
                self.assertTrue(headers.get('X-Request-Id'))

    def test_user_can_read_catalog_and_detail(self):
        doc = self.seed()
        status, body, _ = self.api.request('GET', '/exercises', role='USER')
        self.assertEqual(status, 200)
        self.assertEqual(set(body), {'data', 'next', 'has_more'})
        self.assertEqual(body.get('data')[0].get('name'), 'Push-up')
        status, body, _ = self.api.request('GET', '/exercises/' + str(doc.id), role='USER')
        self.assertEqual(status, 200)
        self.assertEqual(body.get('id'), str(doc.id))
        self.assertNotIn('_id', body)
        self.assertNotIn('description', body)

    def test_user_cannot_mutate_catalog(self):
        doc = self.seed()
        path = '/exercises/' + str(doc.id)
        for method, url, payload in (('POST', '/exercises', self.values()), ('PUT', path, {'name': 'Forbidden'}), ('DELETE', path, {})):
            with self.subTest(method=method):
                status, body, _ = self.api.request(method, url, role='USER', payload=payload)
                self.assertEqual(status, 403)
                self.assertEqual(body.get('code'), 'FORBIDDEN')
        self.assertEqual(self.repo.find_by_id(doc.id).name, 'Push-up')
        self.assertEqual(self.db.exercises.count_documents({}), 1)

    def test_admin_crud_and_timestamp_are_consistent(self):
        values = self.values(description='Technique', video_url='https://example.org/video', image_url='https://example.org/image')
        status, created, _ = self.api.request('POST', '/exercises', payload=values)
        self.assertEqual(status, 201)
        exercise_id = created.get('id')
        self.assertTrue(ObjectId.is_valid(exercise_id))
        timestamp = datetime.fromisoformat(created.get('created_at'))
        self.assertEqual(timestamp.utcoffset(), UTC.utcoffset(None))
        path = '/exercises/' + exercise_id
        status, read, _ = self.api.request('GET', path)
        self.assertEqual(status, 200)
        self.assertEqual(read.get('created_at'), created.get('created_at'))
        status, updated, _ = self.api.request('PUT', path, payload={'name': 'Bench press'})
        self.assertEqual(status, 200)
        self.assertEqual(updated.get('name'), 'Bench press')
        self.assertEqual(updated.get('description'), 'Technique')
        self.assertEqual(updated.get('created_at'), created.get('created_at'))
        status, _, _ = self.api.request('DELETE', path)
        self.assertEqual(status, 204)
        self.assertEqual(self.api.request('GET', path)[0], 404)

    def test_partial_and_empty_put_preserve_fields(self):
        doc = self.seed(description='Original', video_url='urn:example:video')
        path = '/exercises/' + str(doc.id)
        before = self.api.request('GET', path)[1]
        status, unchanged, _ = self.api.request('PUT', path, payload={})
        self.assertEqual(status, 200)
        self.assertEqual(unchanged, before)
        status, changed, _ = self.api.request('PUT', path, payload={'description': ''})
        self.assertEqual(status, 200)
        self.assertEqual(changed.get('description'), '')
        self.assertEqual(changed.get('video_url'), 'urn:example:video')
        status, body, _ = self.api.request('PUT', path, payload={'description': None})
        self.assertEqual(status, 400)
        self.assertEqual(body.get('errors')[0].get('field'), 'description')

    def test_create_validation_and_body_type(self):
        for payload in ({}, [], None, True, {'name': 1, 'muscle_groups': 'CHEST', 'equipment': []}):
            with self.subTest(payload=payload):
                status, body, _ = self.api.request('POST', '/exercises', payload=payload)
                self.assertEqual(status, 400)
                self.assertEqual(body.get('code'), 'BAD_REQUEST')
                self.assertEqual(body.get('message'), 'Validation failed')
                self.assertTrue(body.get('errors'))
                for error in body.get('errors'):
                    self.assertIsInstance(error.get('field'), str)
                    self.assertTrue(error.get('message').isascii())
        self.assertEqual(self.db.exercises.count_documents({}), 0)

    def test_invalid_uri_components_are_rejected_on_create_and_update(self):
        doc = self.seed(video_url='urn:example:video', image_url='https://example.org/image')
        path = '/exercises/' + str(doc.id)
        before = self.api.request('GET', path)[1]
        for field in ('video_url', 'image_url'):
            for value in ('https://example.org:abc/video', 'https://example.org/video#part#other', 'https://example.org/[video]'):
                for method, url, payload in (('POST', '/exercises', self.values(**{field: value})), ('PUT', path, {field: value})):
                    with self.subTest(field=field, value=value, method=method):
                        status, body, _ = self.api.request(method, url, payload=payload)
                        self.assertEqual(status, 400)
                        self.assertIn(field, [error.get('field') for error in body.get('errors')])
        self.assertEqual(self.api.request('GET', path)[1], before)
        self.assertEqual(self.db.exercises.count_documents({}), 1)

    def test_unknown_body_keys_are_rejected_by_shared_validation(self):
        forced_id = '507f1f77bcf86cd799439011'
        status, body, _ = self.api.request('POST', '/exercises', payload=self.values(_id=forced_id, created_at='yesterday', extra='ignored'))
        self.assertEqual(status, 400)
        self.assertEqual({error.get('field') for error in body.get('errors')}, {'_id', 'created_at', 'extra'})
        self.assertEqual(self.db.exercises.count_documents({}), 0)

    def test_filters_accept_any_case_with_multiple_values(self):
        self.seed(name='Bench', muscle_groups=['CHEST'], equipment=['DUMBBELL'])
        self.seed(name='Curl', muscle_groups=['ARMS'], equipment=['DUMBBELL'])
        self.seed(name='Excluded', muscle_groups=['BACK'], equipment=['BODYWEIGHT'])
        for muscles, equipment in (('chest,arms', 'dumbbell'), ('ChEsT,ArMs', 'DumBBeLl'), ('CHEST,ARMS', 'DUMBBELL')):
            with self.subTest(muscles=muscles):
                query = urlencode({'muscle_group': muscles, 'equipment': equipment})
                status, body, _ = self.api.request('GET', '/exercises?' + query)
                self.assertEqual(status, 200)
                self.assertEqual([item.get('name') for item in body.get('data')], ['Bench', 'Curl'])

    def test_missing_and_malformed_ids(self):
        path = '/exercises/' + str(ObjectId())
        for method in ('GET', 'PUT', 'DELETE'):
            with self.subTest(method=method):
                status, body, _ = self.api.request(method, path, payload={} if method == 'PUT' else None)
                self.assertEqual(status, 404)
                self.assertEqual(body.get('code'), 'NOT_FOUND')
        for method, expected in (('GET', 404), ('DELETE', 404), ('PUT', 400)):
            with self.subTest(method=method):
                status, body, _ = self.api.request(method, '/exercises/bad', payload={})
                self.assertEqual(status, expected)
                if method == 'PUT':
                    self.assertEqual(body.get('errors')[0].get('field'), 'exercise_id')

    def test_used_exercise_returns_conflict_and_remains_available(self):
        doc = self.seed()
        for reference in (doc.id, str(doc.id)):
            with self.subTest(reference=reference):
                self.db.programs.delete_many({})
                self.db.programs.insert_one({'exercises': [{'exercise_id': reference}]})
                status, body, _ = self.api.request('DELETE', '/exercises/' + str(doc.id))
                self.assertEqual(status, 409)
                self.assertEqual(body, {'code': 'CONFLICT', 'message': 'Exercise is used in one or more programs'})
                self.assertIsNotNone(self.repo.find_by_id(doc.id))

    def test_filters_and_cursor_pagination(self):
        expected = []
        for number in range(5):
            doc = self.seed(name=f'Exercise {number}', muscle_groups=['CHEST' if number % 2 == 0 else 'ARMS'], equipment=['DUMBBELL'])
            expected.append(str(doc.id))
        self.seed(name='Excluded', equipment=['BODYWEIGHT'])
        received = []
        cursor = None
        for page in range(3):
            query = {'muscle_group': 'CHEST,ARMS', 'equipment': 'DUMBBELL', 'limit': 2}
            if cursor is not None:
                query['cursor'] = cursor
            status, body, _ = self.api.request('GET', '/exercises?' + urlencode(query), role='USER')
            self.assertEqual(status, 200)
            received.extend(item.get('id') for item in body.get('data'))
            self.assertNotIn('limit', body)
            self.assertEqual(body.get('has_more'), page < 2)
            cursor = body.get('next')
        self.assertEqual(received, expected)
        self.assertIsNone(cursor)

    def test_default_limit_and_empty_page(self):
        status, body, _ = self.api.request('GET', '/exercises')
        self.assertEqual(status, 200)
        self.assertEqual(body, {'data': [], 'next': None, 'has_more': False})
        for number in range(21):
            self.seed(name=f'Exercise {number}')
        body = self.api.request('GET', '/exercises')[1]
        self.assertEqual(len(body.get('data')), 20)
        self.assertTrue(body.get('has_more'))

    def test_search_is_literal_and_case_insensitive(self):
        self.seed(name='Literal .* exercise')
        self.seed(name='Other', description='Жим лёжа')
        for search, names in (('.*', ['Literal .* exercise']), ('жим', ['Other']), ('[', [])):
            with self.subTest(search=search):
                status, body, _ = self.api.request('GET', '/exercises?' + urlencode({'search': search}))
                self.assertEqual(status, 200)
                self.assertEqual([item.get('name') for item in body.get('data')], names)

    def test_search_handles_nul_and_overlong_literal(self):
        self.seed(name='Contains\x00value')
        self.seed(name='Other', description='x' * 500)
        for search, names in (('\x00', ['Contains\x00value']), ('x' * 40000, [])):
            with self.subTest(search_length=len(search)):
                status, body, _ = self.api.request('GET', '/exercises?' + urlencode({'search': search}))
                self.assertEqual(status, 200)
                self.assertEqual([item.get('name') for item in body.get('data')], names)

    def test_invalid_query_returns_validation_error(self):
        for query, field in (({'limit': 0}, 'limit'), ({'limit': 101}, 'limit'), ({'limit': 'x'}, 'limit'), ({'muscle_group': 'UNKNOWN'}, 'muscle_group'), ({'equipment': 'UNKNOWN'}, 'equipment'), ({'cursor': 'bad'}, 'cursor')):
            with self.subTest(query=query):
                status, body, _ = self.api.request('GET', '/exercises?' + urlencode(query))
                self.assertEqual(status, 400)
                self.assertEqual(body.get('code'), 'BAD_REQUEST')
                self.assertEqual(body.get('errors')[0].get('field'), field)

    def test_auth_routes_still_work(self):
        values = {'email': 'test@example.test', 'password': 'test_password_123'}
        status, _, _ = self.api.request('POST', '/auth/register', role=None, payload=values)
        self.assertEqual(status, 201)
        status, body, _ = self.api.request('POST', '/auth/login', role=None, payload=values)
        self.assertEqual(status, 200)
        self.assertTrue(body.get('access_token'))


if __name__ == '__main__':
    unittest.main()

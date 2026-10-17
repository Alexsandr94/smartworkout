from datetime import UTC, datetime
from urllib.parse import urlencode

from bson import ObjectId
import pytest

from app.repositories.exercises import ExerciseRepository



class TestExerciseAPI:

    @pytest.fixture(autouse=True)
    def setup(self, api):
        self.api = api
        self.db = api.fixture.db
        self.repo = ExerciseRepository(self.db)

    @staticmethod
    def values(**changes):
        return {'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT'], **changes}

    def seed(self, **changes):
        return self.repo.create(self.values(**changes))

    def test_reads_require_authorization(self):
        for path in ('/exercises', '/exercises/507f1f77bcf86cd799439011'):
            status, body, headers = self.api.request('GET', path, role=None)
            assert status == 401
            assert body.get('code') == 'UNAUTHORIZED'
            assert headers.get('X-Request-Id')

    def test_user_can_read_catalog_and_detail(self):
        doc = self.seed()
        status, body, _ = self.api.request('GET', '/exercises', role='USER')
        assert status == 200
        assert set(body) == {'data', 'next', 'has_more'}
        assert body.get('data')[0].get('name') == 'Push-up'
        status, body, _ = self.api.request('GET', '/exercises/' + str(doc.id), role='USER')
        assert status == 200
        assert body.get('id') == str(doc.id)
        assert '_id' not in body
        assert 'description' not in body

    def test_user_cannot_mutate_catalog(self):
        doc = self.seed()
        path = '/exercises/' + str(doc.id)
        for method, url, payload in (('POST', '/exercises', self.values()), ('PUT', path, {'name': 'Forbidden'}), ('DELETE', path, {})):
            status, body, _ = self.api.request(method, url, role='USER', payload=payload)
            assert status == 403
            assert body.get('code') == 'FORBIDDEN'
        assert self.repo.find_by_id(doc.id).name == 'Push-up'
        assert self.db.exercises.count_documents({}) == 1

    def test_admin_crud_and_timestamp_are_consistent(self):
        values = self.values(description='Technique', video_url='https://example.org/video', image_url='https://example.org/image')
        status, created, _ = self.api.request('POST', '/exercises', payload=values)
        assert status == 201
        exercise_id = created.get('id')
        assert ObjectId.is_valid(exercise_id)
        timestamp = datetime.fromisoformat(created.get('created_at'))
        assert timestamp.utcoffset() == UTC.utcoffset(None)
        path = '/exercises/' + exercise_id
        status, read, _ = self.api.request('GET', path)
        assert status == 200
        assert read.get('created_at') == created.get('created_at')
        status, updated, _ = self.api.request('PUT', path, payload={'name': 'Bench press'})
        assert status == 200
        assert updated.get('name') == 'Bench press'
        assert updated.get('description') == 'Technique'
        assert updated.get('created_at') == created.get('created_at')
        status, _, _ = self.api.request('DELETE', path)
        assert status == 204
        assert self.api.request('GET', path)[0] == 404

    def test_partial_and_empty_put_preserve_fields(self):
        doc = self.seed(description='Original', video_url='urn:example:video')
        path = '/exercises/' + str(doc.id)
        before = self.api.request('GET', path)[1]
        status, unchanged, _ = self.api.request('PUT', path, payload={})
        assert status == 200
        assert unchanged == before
        status, changed, _ = self.api.request('PUT', path, payload={'description': ''})
        assert status == 200
        assert changed.get('description') == ''
        assert changed.get('video_url') == 'urn:example:video'
        status, body, _ = self.api.request('PUT', path, payload={'description': None})
        assert status == 400
        assert body.get('errors')[0].get('field') == 'description'

    def test_create_validation_and_body_type(self):
        for payload in ({}, [], None, True, {'name': 1, 'muscle_groups': 'CHEST', 'equipment': []}):
            status, body, _ = self.api.request('POST', '/exercises', payload=payload)
            assert status == 400
            assert body.get('code') == 'BAD_REQUEST'
            assert body.get('message') == 'Validation failed'
            assert body.get('errors')
            for error in body.get('errors'):
                assert isinstance(error.get('field'), str)
                assert error.get('message').isascii()
        assert self.db.exercises.count_documents({}) == 0

    def test_invalid_uri_values_are_rejected_on_create_and_update(self):
        doc = self.seed(video_url='urn:example:video', image_url='https://example.org/image')
        path = '/exercises/' + str(doc.id)
        before = self.api.request('GET', path)[1]
        for field in ('video_url', 'image_url'):
            for value in ('https://example.org:abc/video', 'https:///video', 'https://example.org:0/video', 'https://example.org:65536/video', 'urn:'):
                for method, url, payload in (('POST', '/exercises', self.values(**{field: value})), ('PUT', path, {field: value})):
                    status, body, _ = self.api.request(method, url, payload=payload)
                    assert status == 400
                    assert field in [error.get('field') for error in body.get('errors')]
        assert self.api.request('GET', path)[1] == before
        assert self.db.exercises.count_documents({}) == 1

    @pytest.mark.parametrize('field', ['video_url', 'image_url'])
    @pytest.mark.parametrize('value', [
        'https://example.org/[video]',
        'https://example.org/video#part#other',
        'https://example.org/%zz',
    ])
    def test_project_uri_rules_are_used_for_create_and_update(self, field, value):
        status, created, _ = self.api.request('POST', '/exercises', payload=self.values(**{field: value}))
        assert status == 201
        assert created.get(field) == value
        updated_value = 'https://example.org/updated/[file]'
        path = '/exercises/' + created.get('id')
        status, updated, _ = self.api.request('PUT', path, payload={field: updated_value})
        assert status == 200
        assert updated.get(field) == updated_value
        assert self.api.request('GET', path)[1].get(field) == updated_value

    def test_unknown_body_keys_are_rejected_by_shared_validation(self):
        forced_id = '507f1f77bcf86cd799439011'
        status, body, _ = self.api.request('POST', '/exercises', payload=self.values(_id=forced_id, created_at='yesterday', extra='ignored'))
        assert status == 400
        assert {error.get('field') for error in body.get('errors')} == {'_id', 'created_at', 'extra'}
        assert self.db.exercises.count_documents({}) == 0

    def test_filters_accept_any_case_with_multiple_values(self):
        self.seed(name='Bench', muscle_groups=['CHEST'], equipment=['DUMBBELL'])
        self.seed(name='Curl', muscle_groups=['ARMS'], equipment=['DUMBBELL'])
        self.seed(name='Excluded', muscle_groups=['BACK'], equipment=['BODYWEIGHT'])
        for muscles, equipment in (('chest,arms', 'dumbbell'), ('ChEsT,ArMs', 'DumBBeLl'), ('CHEST,ARMS', 'DUMBBELL')):
            query = urlencode({'muscle_group': muscles, 'equipment': equipment})
            status, body, _ = self.api.request('GET', '/exercises?' + query)
            assert status == 200
            assert [item.get('name') for item in body.get('data')] == ['Bench', 'Curl']

    def test_missing_and_malformed_ids(self):
        path = '/exercises/' + str(ObjectId())
        for method in ('GET', 'PUT', 'DELETE'):
            status, body, _ = self.api.request(method, path, payload={} if method == 'PUT' else None)
            assert status == 404
            assert body.get('code') == 'NOT_FOUND'
        for method, expected in (('GET', 404), ('DELETE', 404), ('PUT', 400)):
            status, body, _ = self.api.request(method, '/exercises/bad', payload={})
            assert status == expected
            if method == 'PUT':
                assert body.get('errors')[0].get('field') == 'exercise_id'

    def test_used_exercise_returns_conflict_and_remains_available(self):
        doc = self.seed()
        for reference in (doc.id, str(doc.id)):
            self.db.programs.delete_many({})
            self.db.programs.insert_one({'exercises': [{'exercise_id': reference}]})
            status, body, _ = self.api.request('DELETE', '/exercises/' + str(doc.id))
            assert status == 409
            assert body == {'code': 'CONFLICT', 'message': 'Exercise is used in one or more programs'}
            assert self.repo.find_by_id(doc.id) is not None

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
            assert status == 200
            received.extend((item.get('id') for item in body.get('data')))
            assert 'limit' not in body
            assert body.get('has_more') == (page < 2)
            cursor = body.get('next')
        assert received == expected
        assert cursor is None

    def test_default_limit_and_empty_page(self):
        status, body, _ = self.api.request('GET', '/exercises')
        assert status == 200
        assert body == {'data': [], 'next': None, 'has_more': False}
        for number in range(21):
            self.seed(name=f'Exercise {number}')
        body = self.api.request('GET', '/exercises')[1]
        assert len(body.get('data')) == 20
        assert body.get('has_more')

    def test_search_is_literal_and_case_insensitive(self):
        self.seed(name='Literal .* exercise')
        self.seed(name='Other', description='Жим лёжа')
        for search, names in (('.*', ['Literal .* exercise']), ('жим', ['Other']), ('[', [])):
            status, body, _ = self.api.request('GET', '/exercises?' + urlencode({'search': search}))
            assert status == 200
            assert [item.get('name') for item in body.get('data')] == names

    def test_search_handles_nul_and_overlong_literal(self):
        self.seed(name='Contains\x00value')
        self.seed(name='Other', description='x' * 500)
        for search, names in (('\x00', ['Contains\x00value']), ('x' * 40000, [])):
            status, body, _ = self.api.request('GET', '/exercises?' + urlencode({'search': search}))
            assert status == 200
            assert [item.get('name') for item in body.get('data')] == names

    def test_invalid_query_returns_validation_error(self):
        for query, field in (({'limit': 0}, 'limit'), ({'limit': 101}, 'limit'), ({'limit': 'x'}, 'limit'), ({'muscle_group': 'UNKNOWN'}, 'muscle_group'), ({'equipment': 'UNKNOWN'}, 'equipment'), ({'cursor': 'bad'}, 'cursor')):
            status, body, _ = self.api.request('GET', '/exercises?' + urlencode(query))
            assert status == 400
            assert body.get('code') == 'BAD_REQUEST'
            assert body.get('errors')[0].get('field') == field

    def test_auth_routes_still_work(self):
        values = {'email': 'test@example.test', 'password': 'test_password_123'}
        status, _, _ = self.api.request('POST', '/auth/register', role=None, payload=values)
        assert status == 201
        status, body, _ = self.api.request('POST', '/auth/login', role=None, payload=values)
        assert status == 200
        assert body.get('access_token')

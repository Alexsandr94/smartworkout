import pytest
from bson import ObjectId
from app.repositories.exercises import ExerciseRepository
from datetime import UTC, datetime


class TestProgramsAPI:

    @pytest.fixture(autouse=True)
    def setup(self, api):
        """Создание тестового упражнения"""
        self.api = api
        self.db = api.fixture.db
        self.exercise_repo = ExerciseRepository(self.db)
        self.exercise = self.exercise_repo.create({
            'name': 'Push-ups',
            'muscle_groups': ['CHEST'],
            'equipment': ['BODYWEIGHT']
        })

    def get_valid_payload(self, **overrides):
        """Вспомогательный метод для генерации валидного JSON программы"""
        payload = {
            "title": "My Test Program",
            "is_public": True,
            "difficulty": "Beginner",
            "exercises": [
                {
                    "exercise_id": str(self.exercise.id),
                    "order": 1,
                    "sets": 3,
                    "reps": 10,
                    "rest_sec": 60
                }
            ]
        }
        payload.update(overrides)
        return payload

    def test_create_program_success(self):
        """1. Успешное создание программы"""
        payload = self.get_valid_payload()
        status, body, _ = self.api.request('POST', '/programs', payload=payload)

        assert status == 201
        assert body['title'] == "My Test Program"
        assert body['exercises'][0]['exercise_name'] == 'Push-ups'
        assert 'id' in body
        assert self.db.programs.count_documents({}) == 1

    def test_create_program_invalid_exercise(self):
        """2. Ошибка 400, если передали несуществующее упражнение"""
        payload = self.get_valid_payload()
        payload['exercises'][0]['exercise_id'] = str(ObjectId())  # Случайный несуществующий ID

        status, body, _ = self.api.request('POST', '/programs', payload=payload)

        assert status == 400
        assert body['code'] == 'BAD_REQUEST'
        assert body['errors'][0]['field'] == 'exercises.0.exercise_id'
        assert body['errors'][0]['message'] == 'Exercise not found'
        assert self.db.programs.count_documents({}) == 0

    def test_create_program_negative_sets(self):
        """3. Валидация DTO: отрицательное количество подходов"""
        payload = self.get_valid_payload()
        payload['exercises'][0]['sets'] = -1

        status, body, _ = self.api.request('POST', '/programs', payload=payload)

        assert status == 400
        assert body['errors'][0]['field'] == 'exercises.0.sets'
        assert body['errors'][0]['message'] == 'sets must be greater than 0'

    def test_patch_program_partial_update(self):
        """4. Частичное обновление (PATCH): меняем только title"""
        _, created, _ = self.api.request('POST', '/programs', payload=self.get_valid_payload())
        program_id = created['id']

        # Обновляем только title
        status, updated, _ = self.api.request('PATCH', f'/programs/{program_id}', payload={"title": "UPDATED Title"})

        assert status == 200
        assert updated['title'] == "UPDATED Title"
        assert len(updated['exercises']) == 1  # Упражнения не стерлись!
        assert updated['is_public'] is True

    def test_patch_program_forbidden_is_public(self):
        """5. Ошибка 400, если в PATCH пытаются передать is_public"""
        _, created, _ = self.api.request('POST', '/programs', payload=self.get_valid_payload())
        program_id = created['id']

        status, body, _ = self.api.request('PATCH', f'/programs/{program_id}', payload={"is_public": False})

        assert status == 400
        assert body['errors'][0]['field'] == 'is_public'
        assert body['errors'][0]['message'] == 'is_public is not allowed'

    def test_access_control_private_program(self):
        """6. Проверка прав: юзер не может прочитать чужую приватную программу (404)"""
        other_author_id = ObjectId()
        doc = {
            "title": "Other Private Program",
            "description": "",
            "is_public": False,
            "difficulty": "",
            "author_id": other_author_id,
            "exercises": [],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        program_id = self.db.programs.insert_one(doc).inserted_id

        status, body, _ = self.api.request('GET', f'/programs/{program_id}', role='USER')

        assert status == 404
        assert body['code'] == 'NOT_FOUND'

    def test_delete_program_cascade(self):
        """7. Каскадное удаление: при удалении программы она исчезает из избранного"""
        # 1. Создаем пользователя USER в базе, чтобы избранное работало
        user_id = ObjectId('507f1f77bcf86cd799439011')  # ID из support.py
        self.db.users.insert_one({
            "_id": user_id,
            "email": "test@example.test",
            "password_hash": "dummy",
            "role": "USER",
            "created_at": datetime.now(UTC),
            "favorite_program_ids": []
        })

        # 2. ADMIN создает публичную программу
        _, created, _ = self.api.request('POST', '/programs', payload=self.get_valid_payload(), role='ADMIN')
        program_id = created['id']

        # 3. USER добавляет её в избранное
        self.api.request('POST', '/me/favorites', payload={"program_id": program_id}, role='USER')

        # 4. ADMIN удаляет программу
        status, _, _ = self.api.request('DELETE', f'/programs/{program_id}', role='ADMIN')
        assert status == 204

        # 5. Проверяем, что программа исчезла из избранного у USER
        user_doc = self.db.users.find_one({"_id": user_id})
        assert ObjectId(program_id) not in user_doc.get('favorite_program_ids', [])

    def test_pagination_public_programs(self):
        """8. Пагинация: проверка лимита и курсоров"""
        # Создаем 3 программы
        for i in range(3):
            self.api.request('POST', '/programs', payload=self.get_valid_payload(title=f"Program {i}"))

        # Запрашиваем по 2 штуки
        status, page1, _ = self.api.request('GET', '/programs?limit=2')

        assert status == 200
        assert len(page1['data']) == 2
        assert page1['has_more'] is True
        assert page1['next'] is not None

        # Запрашиваем следующую страницу по курсору
        status, page2, _ = self.api.request('GET', f"/programs?limit=2&cursor={page1['next']}")

        assert status == 200
        assert len(page2['data']) == 1
        assert page2['has_more'] is False
        assert page2['next'] is None
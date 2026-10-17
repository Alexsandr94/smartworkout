from datetime import UTC, datetime

from bson import ObjectId
from pymongo.errors import WriteError
import pytest

from app.common.pagination import PaginationParams



class TestExerciseRepository:

    @pytest.fixture(autouse=True)
    def setup(self, exercise_repo):
        self.repo = exercise_repo
        self.db = exercise_repo.collection.database

    def create(self, name='Bench press', muscle_groups=None, equipment=None, **extra):
        return self.repo.create({'name': name, 'muscle_groups': muscle_groups or ['CHEST'], 'equipment': equipment or ['DUMBBELL'], **extra})

    def test_create_stores_object_id_and_utc_date(self):
        doc = self.create()
        assert isinstance(doc.id, ObjectId)
        assert isinstance(doc.created_at, datetime)
        assert doc.created_at.utcoffset() == UTC.utcoffset(None)
        stored = self.repo.find_by_id(doc.id)
        assert stored.name == 'Bench press'
        assert stored.description is None

    def test_update_preserves_other_fields(self):
        doc = self.create(description='Technique')
        updated = self.repo.update(doc.id, {'name': 'New name'})
        assert updated.name == 'New name'
        assert updated.description == 'Technique'
        assert updated.equipment == ['DUMBBELL']
        assert self.repo.update(doc.id, {}).name == 'New name'
        assert self.repo.update(ObjectId(), {'name': 'Missing'}) is None

    def test_filters_use_or_inside_and_across_fields(self):
        self.create(name='Bench')
        self.create(name='Curl', muscle_groups=['ARMS'])
        self.create(name='Push-up', equipment=['BODYWEIGHT'])
        self.create(name='Row', muscle_groups=['BACK'])
        matches = self.repo.find_page(muscle_groups=['CHEST', 'ARMS'], equipment=['DUMBBELL'])
        assert {item.name for item in matches} == {'Bench', 'Curl'}

    def test_literal_search_and_case_insensitive_cyrillic(self):
        self.create(name='Literal .* exercise')
        self.create(name='Other', description='Жим лёжа')
        self.create(name='Plain')
        assert [item.name for item in self.repo.find_page(search='.*')] == ['Literal .* exercise']
        assert [item.name for item in self.repo.find_page(search='жим')] == ['Other']
        assert self.repo.find_page(search='[') == []

    def test_cursor_keeps_filtered_pages_disjoint(self):
        expected = []
        for number in range(5):
            expected.append(self.create(name=f'Exercise {number}', muscle_groups=['CHEST' if number % 2 == 0 else 'ARMS']).id)
        self.create(name='Excluded', equipment=['BODYWEIGHT'])
        first = self.repo.find_page(muscle_groups=['CHEST', 'ARMS'], equipment=['DUMBBELL'], pagination=PaginationParams(limit=2))
        assert [item.id for item in first] == expected[:3]
        second = self.repo.find_page(muscle_groups=['CHEST', 'ARMS'], equipment=['DUMBBELL'], pagination=PaginationParams(limit=2, cursor=first[1].id))
        assert [item.id for item in second] == expected[2:5]
        last = self.repo.find_page(muscle_groups=['CHEST', 'ARMS'], equipment=['DUMBBELL'], pagination=PaginationParams(limit=2, cursor=second[1].id))
        assert [item.id for item in last] == expected[4:]

    def test_usage_checks_object_id_and_string_references(self):
        doc = self.create()
        exercise_id = doc.id
        assert not self.repo.is_used_in_programs(exercise_id)
        self.db.programs.insert_one({'exercises': [{'exercise_id': ObjectId()}]})
        assert not self.repo.is_used_in_programs(exercise_id)
        for reference in (exercise_id, str(exercise_id)):
            program_id = self.db.programs.insert_one({'exercises': [{'exercise_id': reference}]}).inserted_id
            assert self.repo.is_used_in_programs(exercise_id)
            self.db.programs.delete_one({'_id': program_id})

    def test_delete_removes_document(self):
        exercise_id = self.create().id
        assert self.repo.delete(exercise_id)
        assert self.repo.find_by_id(exercise_id) is None
        assert not self.repo.delete(exercise_id)

    def test_schema_rejects_extra_fields_empty_arrays_and_invalid_enum(self):
        valid = {'name': 'Exercise', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT'], 'created_at': datetime.now(UTC)}
        for invalid in ({'extra': 'value'}, {'muscle_groups': []}, {'equipment': ['UNKNOWN']}, {'description': None}, {'name': 'x' * 101}):
            with pytest.raises(WriteError):
                self.db.exercises.insert_one({**valid, **invalid})
        self.db.exercises.insert_one({**valid, 'muscle_groups': ['CHEST', 'CHEST']})
        assert self.db.exercises.count_documents({}) == 1

import pytest

from app.models.exercise import Exercise
from app.services.exercises.service import ExerciseService



class TestExerciseModels:

    @pytest.fixture(autouse=True)
    def setup(self, exercise_repo):
        self.model = Exercise
        self.repo = exercise_repo
        self.service = ExerciseService(self.repo)

    def test_repository_and_service_return_models_with_preserved_fields(self):
        created = self.service.create({'name': 'Bench', 'muscle_groups': ['CHEST'], 'equipment': ['DUMBBELL'], 'description': ''})
        assert isinstance(created, self.model)
        assert created.name == 'Bench'
        assert created.description == ''
        found = self.repo.find_by_id(created.id)
        assert isinstance(found, self.model)
        assert found.id == created.id
        updated = self.service.update(created.id, {'name': 'New bench'})
        assert isinstance(updated, self.model)
        assert updated.name == 'New bench'
        assert updated.description == ''

    def test_service_page_contains_models_and_supports_primitive_filters(self):
        self.service.create({'name': 'Bench', 'muscle_groups': ['CHEST'], 'equipment': ['DUMBBELL']})
        self.service.create({'name': 'Row', 'muscle_groups': ['BACK'], 'equipment': ['DUMBBELL']})
        page = self.service.list(muscle_groups=['CHEST'], equipment=['DUMBBELL'])
        assert [item.name for item in page.data] == ['Bench']
        assert isinstance(page.data[0], self.model)
        assert not page.has_more
        assert page.next is None

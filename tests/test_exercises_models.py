import importlib
import unittest

from app.repositories.exercises import ExerciseRepository
from app.services.exercises.service import ExerciseService
from tests.exercises_support import TemporaryDatabase


class ExerciseModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        try:
            self.model = importlib.import_module('app.models.exercise').Exercise
        except ModuleNotFoundError:
            self.fail('Exercise model is not implemented')
        self.fixture = TemporaryDatabase()
        self.addCleanup(self.fixture.close)
        self.repo = ExerciseRepository(self.fixture.db)
        self.service = ExerciseService(self.repo)

    def test_repository_and_service_return_models_with_preserved_fields(self):
        created = self.service.create({'name': 'Bench', 'muscle_groups': ['CHEST'], 'equipment': ['DUMBBELL'], 'description': ''})
        self.assertIsInstance(created, self.model)
        self.assertEqual(created.name, 'Bench')
        self.assertEqual(created.description, '')
        found = self.repo.find_by_id(created.id)
        self.assertIsInstance(found, self.model)
        self.assertEqual(found.id, created.id)
        updated = self.service.update(created.id, {'name': 'New bench'})
        self.assertIsInstance(updated, self.model)
        self.assertEqual(updated.name, 'New bench')
        self.assertEqual(updated.description, '')

    def test_service_page_contains_models_and_supports_primitive_filters(self):
        self.service.create({'name': 'Bench', 'muscle_groups': ['CHEST'], 'equipment': ['DUMBBELL']})
        self.service.create({'name': 'Row', 'muscle_groups': ['BACK'], 'equipment': ['DUMBBELL']})
        page = self.service.list(muscle_groups=['CHEST'], equipment=['DUMBBELL'])
        self.assertEqual([item.name for item in page.data], ['Bench'])
        self.assertIsInstance(page.data[0], self.model)
        self.assertFalse(page.has_more)
        self.assertIsNone(page.next)

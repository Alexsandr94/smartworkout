from datetime import UTC, datetime

from bson import ObjectId
import pytest

from app.common.pagination import PaginationParams
from app.errors.exercises import ExerciseInUseError, ExerciseNotFoundError
from app.models.exercise import Exercise
from app.services.exercises.service import ExerciseService



class RepositoryDouble:

    def __init__(self):
        self.documents = {}
        self.used = set()
        self.page = []
        self.disappear_before_delete = False

    def create(self, values):
        doc = Exercise.from_document({'_id': ObjectId(), 'created_at': datetime.now(UTC), **values})
        self.documents[doc.id] = doc
        return doc

    def find_by_id(self, exercise_id):
        return self.documents.get(exercise_id)

    def update(self, exercise_id, changes):
        doc = self.documents.get(exercise_id)
        if doc is not None:
            for name, value in changes.items():
                setattr(doc, name, value)
        return doc

    def find_page(self, **filters):
        return self.page

    def is_used_in_programs(self, exercise_id):
        return exercise_id in self.used

    def delete(self, exercise_id):
        previous = self.documents.pop(exercise_id, None)
        return previous is not None and (not self.disappear_before_delete)


class TestExerciseService:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.repo = RepositoryDouble()
        self.service = ExerciseService(self.repo)

    def create(self):
        return self.service.create({'name': 'Push-up', 'muscle_groups': ['CHEST'], 'equipment': ['BODYWEIGHT']})

    def test_missing_exercise_raises_not_found(self):
        missing = ObjectId()
        for operation in (lambda: self.service.get(missing), lambda: self.service.update(missing, {'name': 'New'}), lambda: self.service.delete(missing)):
            with pytest.raises(ExerciseNotFoundError) as caught:
                operation()
            assert caught.value.status == 404
            assert caught.value.code == 'NOT_FOUND'

    def test_used_exercise_is_not_deleted(self):
        doc = self.create()
        self.repo.used.add(doc.id)
        with pytest.raises(ExerciseInUseError) as caught:
            self.service.delete(doc.id)
        assert caught.value.status == 409
        assert caught.value.message == 'Exercise is used in one or more programs'
        assert self.service.get(doc.id).name == 'Push-up'

    def test_free_exercise_is_deleted(self):
        doc = self.create()
        self.service.delete(doc.id)
        with pytest.raises(ExerciseNotFoundError):
            self.service.get(doc.id)

    def test_disappearance_during_delete_returns_not_found(self):
        doc = self.create()
        self.repo.disappear_before_delete = True
        with pytest.raises(ExerciseNotFoundError):
            self.service.delete(doc.id)

    def test_update_returns_changed_document(self):
        doc = self.create()
        result = self.service.update(doc.id, {'name': 'Bench press'})
        assert result.name == 'Bench press'
        assert result.equipment == ['BODYWEIGHT']

    def test_extra_page_result_is_not_returned(self):
        self.repo.page = [self.create() for _ in range(3)]
        result = self.service.list(pagination=PaginationParams(limit=2))
        assert len(result.data) == 2
        assert result.has_more
        assert result.limit == 2
        assert result.next == str(self.repo.page[1].id)

    def test_last_and_empty_pages_have_no_next_cursor(self):
        for size in (0, 1, 2):
            self.repo.page = [self.create() for _ in range(size)]
            result = self.service.list(pagination=PaginationParams(limit=2))
            assert not result.has_more
            assert result.next is None
            assert len(result.data) == size

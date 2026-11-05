import pytest
from bson import ObjectId

from app.dtos.base import DTOValidationError
from app.dtos.session import SessionFinishDTO, SessionListDTO, SessionStartDTO


def finish_exercise(**changes):
    item = {
        "exercise_id": str(ObjectId()),
        "exercise_name": "Push-ups",
        "order": 1,
        "planned_sets": 2,
        "planned_reps": 10,
        "rest_sec": 60,
        "completed_sets": 2,
        "actual_reps": [10, 8],
        "is_completed": True,
        "is_skipped": False,
    }
    item.update(changes)
    return item


def test_start_dto_accepts_program_without_overrides():
    dto = SessionStartDTO.from_dict({"program_id": str(ObjectId())})
    assert dto.exercises is None


def test_start_dto_accepts_optional_exercises():
    dto = SessionStartDTO.from_dict({
        "program_id": str(ObjectId()),
        "exercises": [{
            "exercise_id": str(ObjectId()),
            "order": 1,
            "sets": 3,
            "reps": 10,
            "rest_sec": 60,
        }],
    })
    assert dto.exercises_document()[0]["sets"] == 3


def test_start_dto_rejects_empty_override_list():
    with pytest.raises(DTOValidationError) as exc:
        SessionStartDTO.from_dict({
            "program_id": str(ObjectId()),
            "exercises": [],
        })
    assert exc.value.errors[0]["field"] == "exercises"


def test_session_list_dto_builds_pagination():
    cursor = str(ObjectId())
    dto = SessionListDTO.from_dict({"limit": "5", "cursor": cursor})
    assert dto.pagination.limit == 5
    assert dto.pagination.cursor == ObjectId(cursor)


def test_finish_dto_validates_result_shape():
    dto = SessionFinishDTO.from_dict({"exercises": [finish_exercise()]})
    assert dto.exercises_document()[0]["actual_reps"] == [10, 8]


@pytest.mark.parametrize("payload", [{}, {"exercises": []}])
def test_finish_dto_requires_results(payload):
    with pytest.raises(DTOValidationError) as exc:
        SessionFinishDTO.from_dict(payload)
    assert any(error["field"] == "exercises" for error in exc.value.errors)


def test_finish_dto_requires_snapshot_fields():
    item = finish_exercise()
    item.pop("order")
    with pytest.raises(DTOValidationError) as exc:
        SessionFinishDTO.from_dict({"exercises": [item]})
    assert any(error["field"] == "exercises.0.order" for error in exc.value.errors)


def test_finish_dto_rejects_reps_length_mismatch():
    with pytest.raises(DTOValidationError) as exc:
        SessionFinishDTO.from_dict({
            "exercises": [finish_exercise(actual_reps=[10])],
        })
    assert any(error["field"] == "exercises.0.actual_reps" for error in exc.value.errors)

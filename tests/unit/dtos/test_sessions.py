import pytest
from bson import ObjectId

from app.dtos.base import DTOValidationError
from app.dtos.session import SessionFinishDTO, SessionStartDTO


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


def test_finish_dto_validates_result_shape():
    dto = SessionFinishDTO.from_dict({
        "exercises": [{
            "exercise_id": str(ObjectId()),
            "completed_sets": 2,
            "actual_reps": [10, 8],
            "is_completed": False,
            "is_skipped": False,
        }],
    })
    assert dto.exercises_document()[0]["actual_reps"] == [10, 8]


def test_finish_dto_rejects_reps_length_mismatch():
    with pytest.raises(DTOValidationError) as exc:
        SessionFinishDTO.from_dict({
            "exercises": [{
                "exercise_id": str(ObjectId()),
                "completed_sets": 2,
                "actual_reps": [10],
                "is_completed": False,
                "is_skipped": False,
            }],
        })
    assert any(error["field"] == "exercises.0.actual_reps" for error in exc.value.errors)

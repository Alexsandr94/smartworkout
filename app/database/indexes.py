import logging

from pymongo import ASCENDING, DESCENDING, IndexModel

from .client import get_db
from .collections import EXERCISES, PROGRAMS, USERS, WORKOUT_SESSIONS

logger = logging.getLogger(__name__)

INDEXES = {
    EXERCISES: [
        IndexModel([("muscle_groups", ASCENDING), ("_id", ASCENDING)], name="idx_exercise_muscle_groups"),
        IndexModel([("equipment", ASCENDING), ("_id", ASCENDING)], name="idx_exercise_equipment"),
    ],
    PROGRAMS: [
        IndexModel([("exercises.exercise_id", ASCENDING)], name="idx_program_exercise_id"),
    ],
    WORKOUT_SESSIONS: [
        IndexModel(
            [("user_id", ASCENDING), ("started_at", DESCENDING)],
            name="idx_session_user_started_at",
        ),
        IndexModel(
            [("user_id", ASCENDING), ("_id", DESCENDING)],
            name="idx_session_user_id",
        ),
        IndexModel(
            [("source_program_id", ASCENDING)],
            name="idx_session_source_program_id",
        ),
    ],
    USERS: [
        IndexModel(
            [("email", ASCENDING)],
            unique=True,
            name="uniq_email",
        ),
        IndexModel(
            [("favorite_program_ids", ASCENDING)],
            name="idx_favorite_program_ids",
        ),
    ],
}

def ensure_indexes() -> None:
    db = get_db()

    for name, index_models in INDEXES.items():
        result = db[name].create_indexes(index_models)
        logger.info({
            "event": "indexes_ensured",
            "collection": name,
            "created": result,
        })

import logging

from pymongo import ASCENDING, IndexModel

from .client import get_db
from .collections import EXERCISES, PROGRAMS, USERS

logger = logging.getLogger(__name__)

INDEXES = {
    EXERCISES: [
        IndexModel([("muscle_groups", ASCENDING), ("_id", ASCENDING)], name="idx_exercise_muscle_groups"),
        IndexModel([("equipment", ASCENDING), ("_id", ASCENDING)], name="idx_exercise_equipment"),
    ],
    PROGRAMS: [
        IndexModel([("exercises.exercise_id", ASCENDING)], name="idx_program_exercise_id"),
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

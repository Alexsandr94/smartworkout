import logging

from .client import get_db
from .collections import EXERCISES, USERS, WORKOUT_SESSIONS
from app.models.exercise import DESCRIPTION_MAX_LENGTH, EQUIPMENT, MUSCLE_GROUPS, NAME_MAX_LENGTH

logger = logging.getLogger(__name__)

VALIDATORS = {
    EXERCISES: {
        "schema": {
            "bsonType": "object",
            "required": ["name", "muscle_groups", "equipment", "created_at"],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "name": {"bsonType": "string", "minLength": 1, "maxLength": NAME_MAX_LENGTH},
                "description": {"bsonType": "string", "maxLength": DESCRIPTION_MAX_LENGTH},
                "muscle_groups": {
                    "bsonType": "array", "minItems": 1,
                    "items": {"bsonType": "string", "enum": list(MUSCLE_GROUPS)},
                },
                "equipment": {
                    "bsonType": "array", "minItems": 1,
                    "items": {"bsonType": "string", "enum": list(EQUIPMENT)},
                },
                "video_url": {"bsonType": "string"},
                "image_url": {"bsonType": "string"},
                "created_at": {"bsonType": "date"},
            },
            "additionalProperties": False,
        },
        "validationLevel": "strict",
        "validationAction": "error",
    },

    WORKOUT_SESSIONS: {
        "schema": {
            "bsonType": "object",
            "required": [
                "user_id",
                "source_program_id",
                "source_program_title",
                "started_at",
                "exercises",
            ],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "user_id": {"bsonType": "objectId"},
                "source_program_id": {"bsonType": "objectId"},
                "source_program_title": {"bsonType": "string", "minLength": 1},
                "started_at": {"bsonType": "date"},
                "finished_at": {"bsonType": "date"},
                "duration_sec": {"bsonType": "int", "minimum": 0},
                "exercises": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": [
                            "exercise_id",
                            "exercise_name",
                            "order",
                            "planned_sets",
                            "planned_reps",
                            "rest_sec",
                            "completed_sets",
                            "actual_reps",
                            "is_completed",
                            "is_skipped",
                        ],
                        "properties": {
                            "exercise_id": {"bsonType": "objectId"},
                            "exercise_name": {"bsonType": "string", "minLength": 1},
                            "order": {"bsonType": "int", "minimum": 1},
                            "planned_sets": {"bsonType": "int", "minimum": 1},
                            "planned_reps": {"bsonType": "int", "minimum": 1},
                            "rest_sec": {"bsonType": "int", "minimum": 0},
                            "completed_sets": {"bsonType": "int", "minimum": 0},
                            "actual_reps": {
                                "bsonType": "array",
                                "items": {"bsonType": "int", "minimum": 0},
                            },
                            "is_completed": {"bsonType": "bool"},
                            "is_skipped": {"bsonType": "bool"},
                        },
                        "additionalProperties": False,
                    },
                },
            },
            "additionalProperties": False,
        },
        "validationLevel": "strict",
        "validationAction": "error",
    },
    USERS: {
        "schema": {
            "bsonType": "object",
            "required": ["email", "password_hash", "role", "created_at"],
            "properties": {
                "_id": {"bsonType": "objectId"},
                "email": {
                    "bsonType": "string",
                    "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$",
                },
                "role": {
                    "bsonType": "string",
                    "enum": ["USER", "ADMIN"],
                    "description": "User role",
                },
                "password_hash": {
                    "bsonType": "string",
                    "minLength": 1,
                    "description": "Password hash must not be empty",
                },
                "created_at": {"bsonType": "date"},
                "favorite_program_ids": {
                    "bsonType": "array",
                    "items": {"bsonType": "objectId"},
                    "uniqueItems": True,
                    "description": "IDs of programs added to favorites",
                },
            },
            "additionalProperties": False,
        },
        "validationLevel": "strict",
        "validationAction": "error",
    },
}


def ensure_schema() -> None:
    db = get_db()
    existing = set(db.list_collection_names())

    for name, spec in VALIDATORS.items():
        validator = {"$jsonSchema": spec["schema"]}
        level = spec.get("validationLevel", "strict")
        action = spec.get("validationAction", "error")

        if name not in existing:
            db.create_collection(
                name,
                validator=validator,
                validationLevel=level,
                validationAction=action,
            )
            logger.info({"event": "collection_created", "collection": name})
        else:
            db.command({
                "collMod": name,
                "validator": validator,
                "validationLevel": level,
                "validationAction": action,
            })
            logger.info({"event": "collection_validator_updated", "collection": name})

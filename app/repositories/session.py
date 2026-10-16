from datetime import UTC, datetime

from pymongo.collection import Collection
from pymongo.database import Database


from app.database.collections import WORKOUT_SESSIONS


class SessionRepository:
    def __init__(self, db: Database):
        self.collection: Collection = db[WORKOUT_SESSIONS]

    def create(
            self,
            user_id,
            source_program_id,
            exercises: list[dict],
    ) -> dict:
        doc = {
            "user_id": user_id,
            "source_program_id": source_program_id,
            "started_at": datetime.now(UTC),
            "exercises": exercises,
        }

        result = self.collection.insert_one(doc)

        doc["_id"] = result.inserted_id

        return doc
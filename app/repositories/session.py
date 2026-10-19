from datetime import UTC, datetime
from bson import ObjectId
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

    def find_by_id(self, session_id: ObjectId) -> dict | None:
        return self.collection.find_one({"_id": session_id})

    def find_by_user_id(self, user_id: ObjectId) -> list[dict]:
        sessions = self.collection.find(
            {"user_id": user_id}
        ).sort("started_at", -1)

        return list(sessions)

    def finish(
            self,
            session_id: ObjectId,
            finished_at: datetime,
            duration_sec: int,
    ) -> bool:
        result = self.collection.update_one(
            {
                "_id": session_id,
                "finished_at": {"$exists": False},
            },
            {
                "$set": {
                    "finished_at": finished_at,
                    "duration_sec": duration_sec,
                }
            },
        )

        return result.modified_count == 1
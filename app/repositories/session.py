from datetime import UTC, datetime

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database

from app.common.pagination import PaginationParams
from app.database.collections import EXERCISES, PROGRAMS, WORKOUT_SESSIONS


class SessionRepository:
    def __init__(self, db: Database):
        self.collection: Collection = db[WORKOUT_SESSIONS]
        self.programs: Collection = db[PROGRAMS]
        self.exercises: Collection = db[EXERCISES]

    def create(
        self,
        user_id: ObjectId,
        source_program_id: ObjectId,
        source_program_title: str,
        exercises: list[dict],
    ) -> dict:
        doc = {
            "user_id": user_id,
            "source_program_id": source_program_id,
            "source_program_title": source_program_title,
            "started_at": datetime.now(UTC),
            "exercises": exercises,
        }

        result = self.collection.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def find_by_id(self, session_id: ObjectId) -> dict | None:
        return self.collection.find_one({"_id": session_id})

    def find_page_by_user_id(
        self,
        user_id: ObjectId,
        pagination: PaginationParams,
    ) -> list[dict]:
        query: dict = {"user_id": user_id}
        if pagination.cursor is not None:
            query["_id"] = {"$lt": pagination.cursor}

        return list(
            self.collection.find(query)
            .sort("_id", -1)
            .limit(pagination.limit + 1)
        )

    def find_program_by_id(self, program_id: ObjectId) -> dict | None:
        return self.programs.find_one({"_id": program_id})

    def get_exercise_names(self, exercise_ids: list[ObjectId]) -> dict[ObjectId, str]:
        cursor = self.exercises.find(
            {"_id": {"$in": exercise_ids}},
            {"_id": 1, "name": 1},
        )
        return {document["_id"]: document["name"] for document in cursor}

    def finish(
        self,
        session_id: ObjectId,
        user_id: ObjectId,
        finished_at: datetime,
        duration_sec: int,
        exercises: list[dict],
    ) -> bool:
        result = self.collection.update_one(
            {
                "_id": session_id,
                "user_id": user_id,
                "finished_at": {"$exists": False},
            },
            {
                "$set": {
                    "finished_at": finished_at,
                    "duration_sec": duration_sec,
                    "exercises": exercises,
                }
            },
        )
        return result.modified_count == 1

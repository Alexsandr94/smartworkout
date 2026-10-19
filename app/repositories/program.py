from datetime import datetime, UTC
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId
from app.database.collections import PROGRAMS, EXERCISES


class ProgramRepository:
    def __init__(self, db: Database):
        self.collection: Collection = db[PROGRAMS]
        self.exercises_collection: Collection = db[EXERCISES]

    def create(self, data: dict, author_id: str) -> dict:
        processed_exercises = []

        for ex in data["exercises"]:
            ex_obj_id = ObjectId(ex["exercise_id"])

            exercise_doc = self.exercises_collection.find_one({"_id": ex_obj_id})
            ex_name = exercise_doc["name"] if exercise_doc else "Unknown Exercise"

            processed_exercises.append({
                "exercise_id": ex_obj_id,
                "exercise_name": ex_name,
                "order": ex["order"],
                "sets": ex["sets"],
                "reps": ex["reps"],
                "rest_sec": ex["rest_sec"]
            })

        now = datetime.now(UTC)
        doc = {
            "title": data["title"],
            "description": data.get("description", ""),
            "is_public": data["is_public"],
            "difficulty": data.get("difficulty", ""),
            "author_id": ObjectId(author_id),
            "exercises": processed_exercises,
            "created_at": now,
            "updated_at": now
        }

        result = self.collection.insert_one(doc)

        doc["_id"] = result.inserted_id
        return doc

    def get_all(self, user_id: str) -> list[dict]:
        query = {
            "$or": [
                {"author_id": ObjectId(user_id)},
                {"is_public": True}
            ]
        }
        cursor = self.collection.find(query).sort("created_at", -1)
        return list(cursor)

    def get_by_id(self, program_id: str) -> dict | None:
        return self.collection.find_one({"_id": ObjectId(program_id)})

    def update(self, program_id: str, data: dict) -> dict | None:
        update_doc = {
            "title": data["title"],
            "description": data.get("description", ""),
            "is_public": data["is_public"],
            "difficulty": data.get("difficulty", ""),
            "exercises": self._prepare_exercises(data["exercises"]),
            "updated_at": datetime.now(UTC)
        }

        result = self.collection.update_one(
            {"_id": ObjectId(program_id)},
            {"$set": update_doc}
        )

        if result.matched_count == 0:
            return None

        return self.get_by_id(program_id)

    def _prepare_exercises(self, exercises_data: list[dict]) -> list[dict]:
        processed_exercises = []
        for ex in exercises_data:
            ex_obj_id = ObjectId(ex["exercise_id"])
            exercise_doc = self.exercises_collection.find_one({"_id": ex_obj_id})
            ex_name = exercise_doc["name"] if exercise_doc else "Unknown Exercise"

            processed_exercises.append({
                "exercise_id": ex_obj_id,
                "exercise_name": ex_name,
                "order": ex["order"],
                "sets": ex["sets"],
                "reps": ex["reps"],
                "rest_sec": ex["rest_sec"]
            })
        return processed_exercises

    def delete(self, program_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(program_id)})
        return result.deleted_count > 0
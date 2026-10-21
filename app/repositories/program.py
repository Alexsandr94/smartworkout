from datetime import datetime, UTC
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo import ASCENDING
from bson import ObjectId
from app.database.collections import PROGRAMS, EXERCISES
from app.common.pagination import PaginationParams


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

    def find_page(self, user_id: str, *, only_my: bool, pagination: PaginationParams) -> list[dict]:
        query = {}

        if only_my:
            query["author_id"] = ObjectId(user_id)
        else:
            query["is_public"] = True

        if pagination.cursor is not None:
            query["_id"] = {"$gt": pagination.cursor}

        cursor = self.collection.find(query).sort("_id", ASCENDING).limit(pagination.limit + 1)
        return list(cursor)

    def get_by_id(self, program_id: str) -> dict | None:
        return self.collection.find_one({"_id": ObjectId(program_id)})

    def update(self, program_id: str, data: dict) -> dict | None:
        update_doc = {}

        if "title" in data:
            update_doc["title"] = data["title"]
        if "description" in data:
            update_doc["description"] = data["description"]
        if "difficulty" in data:
            update_doc["difficulty"] = data["difficulty"]
        if "exercises" in data:
            update_doc["exercises"] = self._prepare_exercises(data["exercises"])

        update_doc["updated_at"] = datetime.now(UTC)

        if not update_doc:
            return self.get_by_id(program_id)

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

    def get_existing_exercise_ids(self, exercise_ids: list[ObjectId]) -> set[ObjectId]:
        cursor = self.exercises_collection.find({"_id": {"$in": exercise_ids}}, {"_id": 1})
        return {doc["_id"] for doc in cursor}

    def delete(self, program_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(program_id)})

        if result.deleted_count > 0:
            users_collection = self.collection.database["users"]
            users_collection.update_many(
                {"favorite_program_ids": ObjectId(program_id)},
                {"$pull": {"favorite_program_ids": ObjectId(program_id)}}
            )

        return result.deleted_count > 0
import re
from collections.abc import Sequence
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import ASCENDING, ReturnDocument
from pymongo.database import Database

from app.common.pagination import PaginationParams
from app.database.collections import EXERCISES, PROGRAMS
from app.models.exercise import DESCRIPTION_MAX_LENGTH, NAME_MAX_LENGTH, Exercise


class ExerciseRepository:
    def __init__(self, db: Database):
        self.collection = db[EXERCISES]
        self.programs = db[PROGRAMS]

    def create(self, values: dict[str, object]) -> Exercise:
        document = {**values, 'created_at': datetime.now(UTC)}
        result = self.collection.insert_one(document)
        document['_id'] = result.inserted_id
        return Exercise.from_document(document)

    def find_by_id(self, exercise_id: ObjectId) -> Exercise | None:
        document = self.collection.find_one({'_id': exercise_id})
        return Exercise.from_document(document) if document is not None else None

    def find_page(
        self, *, muscle_groups: Sequence[str] | None = None,
        equipment: Sequence[str] | None = None, search: str | None = None,
        pagination: PaginationParams = PaginationParams(),
    ) -> list[Exercise]:
        query = {}
        if muscle_groups is not None:
            query['muscle_groups'] = {'$in': list(muscle_groups)}
        if equipment is not None:
            query['equipment'] = {'$in': list(equipment)}
        if search is not None:
            # No bounded searchable field can contain a longer literal.
            if len(search) > max(NAME_MAX_LENGTH, DESCRIPTION_MAX_LENGTH):
                return []
            pattern = {'$regex': re.escape(search).replace('\x00', r'\x00'), '$options': 'i'}
            query['$or'] = [{'name': pattern}, {'description': pattern}]
        if pagination.cursor is not None:
            query['_id'] = {'$gt': pagination.cursor}
        documents = self.collection.find(query).sort('_id', ASCENDING).limit(pagination.limit + 1)
        return [Exercise.from_document(document) for document in documents]

    def update(self, exercise_id: ObjectId, changes: dict[str, object]) -> Exercise | None:
        if not changes:
            return self.find_by_id(exercise_id)
        document = self.collection.find_one_and_update(
            {'_id': exercise_id}, {'$set': changes}, return_document=ReturnDocument.AFTER,
        )
        return Exercise.from_document(document) if document is not None else None

    def is_used_in_programs(self, exercise_id: ObjectId) -> bool:
        return self.programs.find_one(
            {'exercises.exercise_id': {'$in': [exercise_id, str(exercise_id)]}}, {'_id': 1},
        ) is not None

    def delete(self, exercise_id: ObjectId) -> bool:
        return self.collection.delete_one({'_id': exercise_id}).deleted_count == 1

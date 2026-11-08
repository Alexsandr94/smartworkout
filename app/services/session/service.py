from datetime import UTC, datetime

from bson import ObjectId

from app.common.pagination import Page, PaginationParams, paginate
from app.dtos.base import DTOValidationError
from app.errors.session import (
    SessionAlreadyFinishedError,
    SessionNotFoundError,
    SessionProgramNotFoundError,
)
from app.repositories.session import SessionRepository


class SessionService:
    def __init__(self, session_repo: SessionRepository):
        self.session_repo = session_repo

    def get_user_sessions(
        self,
        user_id: str,
        pagination: PaginationParams,
    ) -> Page[dict]:
        sessions = self.session_repo.find_page_by_user_id(
            ObjectId(user_id),
            pagination,
        )
        page = paginate(sessions, pagination, key=lambda session: session["_id"])
        page.data = [self._to_short_view(session) for session in page.data]
        return page

    def get_user_session(self, user_id: str, session_id: str) -> dict:
        if not ObjectId.is_valid(session_id):
            raise SessionNotFoundError()

        session = self.session_repo.find_by_id(ObjectId(session_id))
        if session is None or session.get("user_id") != ObjectId(user_id):
            raise SessionNotFoundError()

        return session

    def start_session(
        self,
        user_id: str,
        program_id: str,
        exercises: list[dict] | None = None,
    ) -> dict:
        user_obj_id = ObjectId(user_id)
        program_obj_id = ObjectId(program_id)

        program = self.session_repo.find_program_by_id(program_obj_id)
        if program is None:
            raise SessionProgramNotFoundError()

        author_id = program.get("author_id")
        is_owner = author_id == user_obj_id
        if not program.get("is_public", False) and not is_owner:
            raise SessionProgramNotFoundError()

        program_exercises = program.get("exercises", [])
        if exercises is None:
            snapshot = self._snapshot_from_program(program_exercises)
        else:
            snapshot = self._snapshot_from_override(exercises, program_exercises)

        return self.session_repo.create(
            user_id=user_obj_id,
            source_program_id=program_obj_id,
            source_program_title=program.get("title", ""),
            exercises=snapshot,
        )

    def finish_session(
        self,
        user_id: str,
        session_id: str,
        results: list[dict],
    ) -> dict:
        if not ObjectId.is_valid(session_id):
            raise SessionNotFoundError()

        user_obj_id = ObjectId(user_id)
        session_obj_id = ObjectId(session_id)

        session = self.session_repo.find_by_id(session_obj_id)
        if session is None or session.get("user_id") != user_obj_id:
            raise SessionNotFoundError()

        if session.get("finished_at") is not None:
            raise SessionAlreadyFinishedError()

        exercises = self._apply_results(session.get("exercises", []), results)

        finished_at = datetime.now(UTC)
        started_at = session["started_at"]
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        duration_sec = max(0, int((finished_at - started_at).total_seconds()))

        updated = self.session_repo.finish(
            session_id=session_obj_id,
            user_id=user_obj_id,
            finished_at=finished_at,
            duration_sec=duration_sec,
            exercises=exercises,
        )

        if not updated:
            raise SessionAlreadyFinishedError()

        return self.session_repo.find_by_id(session_obj_id)

    def _snapshot_from_program(self, exercises: list[dict]) -> list[dict]:
        snapshot = []

        for exercise in exercises:
            exercise_id = exercise.get("exercise_id")
            if not isinstance(exercise_id, ObjectId):
                exercise_id = ObjectId(exercise_id)

            snapshot.append(self._snapshot_exercise(
                exercise_id=exercise_id,
                exercise_name=exercise.get("exercise_name", "Unknown Exercise"),
                order=exercise["order"],
                sets=exercise["sets"],
                reps=exercise["reps"],
                rest_sec=exercise["rest_sec"],
            ))

        return sorted(snapshot, key=lambda item: item["order"])

    def _snapshot_from_override(
        self,
        exercises: list[dict],
        program_exercises: list[dict],
    ) -> list[dict]:
        allowed_ids = {
            ObjectId(item["exercise_id"])
            if not isinstance(item["exercise_id"], ObjectId)
            else item["exercise_id"]
            for item in program_exercises
        }
        program_names: dict[ObjectId, str] = {}
        for item in program_exercises:
            exercise_id = item["exercise_id"]
            if not isinstance(exercise_id, ObjectId):
                exercise_id = ObjectId(exercise_id)
            name = item.get("exercise_name")
            if name and exercise_id not in program_names:
                program_names[exercise_id] = name

        exercise_ids = [ObjectId(exercise["exercise_id"]) for exercise in exercises]
        missing_names = [exercise_id for exercise_id in set(exercise_ids) if exercise_id not in program_names]
        if missing_names:
            program_names.update(self.session_repo.get_exercise_names(missing_names))

        errors = []
        seen_orders = set()

        for index, (exercise, exercise_id) in enumerate(zip(exercises, exercise_ids)):
            if exercise_id not in allowed_ids:
                errors.append({
                    "field": f"exercises.{index}.exercise_id",
                    "message": "exercise is not part of the source program",
                })

            order = exercise["order"]
            if order in seen_orders:
                errors.append({
                    "field": f"exercises.{index}.order",
                    "message": "order must be unique within a session",
                })
            seen_orders.add(order)

        if errors:
            raise DTOValidationError(errors)

        snapshot = []
        for exercise, exercise_id in zip(exercises, exercise_ids):
            snapshot.append(self._snapshot_exercise(
                exercise_id=exercise_id,
                exercise_name=program_names.get(exercise_id, "Unknown Exercise"),
                order=exercise["order"],
                sets=exercise["sets"],
                reps=exercise["reps"],
                rest_sec=exercise["rest_sec"],
            ))

        return sorted(snapshot, key=lambda item: item["order"])

    @staticmethod
    def _snapshot_exercise(
        *,
        exercise_id: ObjectId,
        exercise_name: str,
        order: int,
        sets: int,
        reps: int,
        rest_sec: int,
    ) -> dict:
        return {
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "order": order,
            "planned_sets": sets,
            "planned_reps": reps,
            "rest_sec": rest_sec,
            "completed_sets": 0,
            "actual_reps": [],
            "is_completed": False,
            "is_skipped": False,
        }

    def _apply_results(
        self,
        exercises: list[dict],
        results: list[dict],
    ) -> list[dict]:
        by_key = {
            (exercise["exercise_id"], exercise["order"]): exercise
            for exercise in exercises
        }
        result_keys = set()
        errors = []

        snapshot_fields = (
            "exercise_name",
            "order",
            "planned_sets",
            "planned_reps",
            "rest_sec",
        )

        for index, result in enumerate(results):
            exercise_id = ObjectId(result["exercise_id"])
            key = (exercise_id, result["order"])

            if key in result_keys:
                errors.append({
                    "field": f"exercises.{index}.order",
                    "message": "exercise result is duplicated",
                })
                continue
            result_keys.add(key)

            planned = by_key.get(key)
            if planned is None:
                errors.append({
                    "field": f"exercises.{index}.exercise_id",
                    "message": "exercise is not part of this session",
                })
                continue

            for field in snapshot_fields:
                if result[field] != planned[field]:
                    errors.append({
                        "field": f"exercises.{index}.{field}",
                        "message": f"{field} does not match the session snapshot",
                    })

            if result["completed_sets"] > planned["planned_sets"]:
                errors.append({
                    "field": f"exercises.{index}.completed_sets",
                    "message": "completed_sets cannot exceed planned_sets",
                })

            if result["is_completed"] and result["completed_sets"] != planned["planned_sets"]:
                errors.append({
                    "field": f"exercises.{index}.is_completed",
                    "message": "completed exercise must have all planned sets completed",
                })

            if result["is_skipped"] and result["completed_sets"] != 0:
                errors.append({
                    "field": f"exercises.{index}.completed_sets",
                    "message": "skipped exercise cannot have completed sets",
                })

        if errors:
            raise DTOValidationError(errors)

        updated = [dict(exercise) for exercise in exercises]
        updated_by_key = {
            (exercise["exercise_id"], exercise["order"]): exercise
            for exercise in updated
        }

        for result in results:
            exercise_id = ObjectId(result["exercise_id"])
            exercise = updated_by_key[(exercise_id, result["order"])]
            exercise["completed_sets"] = result["completed_sets"]
            exercise["actual_reps"] = list(result["actual_reps"])
            exercise["is_completed"] = result["is_completed"]
            exercise["is_skipped"] = result["is_skipped"]

        return updated

    @staticmethod
    def _to_short_view(session: dict) -> dict:
        result = {
            "_id": session["_id"],
            "source_program_id": session["source_program_id"],
            "source_program_title": session.get("source_program_title", ""),
            "started_at": session["started_at"],
        }
        if session.get("finished_at") is not None:
            result["finished_at"] = session["finished_at"]
        if session.get("duration_sec") is not None:
            result["duration_sec"] = session["duration_sec"]
        return result

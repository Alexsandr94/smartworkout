from datetime import UTC, datetime

from bson import ObjectId

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

    def get_user_sessions(self, user_id: str) -> list[dict]:
        return self.session_repo.find_by_user_id(ObjectId(user_id))

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

        if exercises is None:
            snapshot = self._snapshot_from_program(program.get("exercises", []))
        else:
            snapshot = self._snapshot_from_override(exercises)

        return self.session_repo.create(
            user_id=user_obj_id,
            source_program_id=program_obj_id,
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

    def _snapshot_from_override(self, exercises: list[dict]) -> list[dict]:
        exercise_ids = [ObjectId(exercise["exercise_id"]) for exercise in exercises]
        names = self.session_repo.get_exercise_names(exercise_ids)

        errors = []
        for index, exercise_id in enumerate(exercise_ids):
            if exercise_id not in names:
                errors.append({
                    "field": f"exercises.{index}.exercise_id",
                    "message": "Exercise not found",
                })

        if errors:
            raise DTOValidationError(errors)

        snapshot = []
        for exercise, exercise_id in zip(exercises, exercise_ids):
            snapshot.append(self._snapshot_exercise(
                exercise_id=exercise_id,
                exercise_name=names[exercise_id],
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
        by_id = {str(exercise["exercise_id"]): exercise for exercise in exercises}
        result_ids = set()
        errors = []

        for index, result in enumerate(results):
            exercise_id = result["exercise_id"]

            if exercise_id in result_ids:
                errors.append({
                    "field": f"exercises.{index}.exercise_id",
                    "message": "exercise result is duplicated",
                })
                continue
            result_ids.add(exercise_id)

            planned = by_id.get(exercise_id)
            if planned is None:
                errors.append({
                    "field": f"exercises.{index}.exercise_id",
                    "message": "exercise is not part of this session",
                })
                continue

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
        updated_by_id = {str(exercise["exercise_id"]): exercise for exercise in updated}

        for result in results:
            exercise = updated_by_id[result["exercise_id"]]
            exercise["completed_sets"] = result["completed_sets"]
            exercise["actual_reps"] = list(result["actual_reps"])
            exercise["is_completed"] = result["is_completed"]
            exercise["is_skipped"] = result["is_skipped"]

        return updated

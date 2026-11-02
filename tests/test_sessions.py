from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId


USER_ID = ObjectId("507f1f77bcf86cd799439011")
OTHER_USER_ID = ObjectId("507f1f77bcf86cd799439012")


class TestSessionsAPI:
    @pytest.fixture(autouse=True)
    def setup(self, api):
        self.api = api
        self.db = api.fixture.db
        self.db.workout_sessions.delete_many({})
        self.db.programs.delete_many({})
        self.db.exercises.delete_many({})

    def seed_exercise(self, name="Push-ups"):
        return self.db.exercises.insert_one({
            "name": name,
            "muscle_groups": ["CHEST"],
            "equipment": ["BODYWEIGHT"],
            "created_at": datetime.now(UTC),
        }).inserted_id

    def seed_program(self, *, author_id=USER_ID, is_public=True):
        exercise_id = self.seed_exercise()
        program_id = self.db.programs.insert_one({
            "title": "Test program",
            "description": "",
            "author_id": author_id,
            "is_public": is_public,
            "difficulty": "Beginner",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "exercises": [{
                "exercise_id": exercise_id,
                "exercise_name": "Push-ups",
                "order": 1,
                "sets": 3,
                "reps": 10,
                "rest_sec": 60,
            }],
        }).inserted_id
        return program_id, exercise_id

    def test_start_session_uses_program_snapshot_when_no_override(self):
        program_id, exercise_id = self.seed_program()

        status, body, _ = self.api.request(
            "POST",
            "/sessions",
            role="USER",
            payload={"program_id": str(program_id)},
        )

        assert status == 201
        assert body["source_program_id"] == str(program_id)
        assert body["exercises"][0]["exercise_id"] == str(exercise_id)
        assert body["exercises"][0]["planned_sets"] == 3
        assert body["exercises"][0]["planned_reps"] == 10
        assert body["exercises"][0]["completed_sets"] == 0

    def test_start_session_uses_override_without_changing_program(self):
        program_id, exercise_id = self.seed_program()

        payload = {
            "program_id": str(program_id),
            "exercises": [{
                "exercise_id": str(exercise_id),
                "order": 1,
                "sets": 5,
                "reps": 8,
                "rest_sec": 90,
            }],
        }
        status, body, _ = self.api.request("POST", "/sessions", role="USER", payload=payload)

        assert status == 201
        assert body["exercises"][0]["planned_sets"] == 5
        assert body["exercises"][0]["planned_reps"] == 8
        assert body["exercises"][0]["rest_sec"] == 90

        program = self.db.programs.find_one({"_id": program_id})
        assert program["exercises"][0]["sets"] == 3
        assert program["exercises"][0]["reps"] == 10
        assert program["exercises"][0]["rest_sec"] == 60

    def test_start_session_rejects_private_foreign_program(self):
        program_id, _ = self.seed_program(author_id=OTHER_USER_ID, is_public=False)
        status, body, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        assert status == 404
        assert body["code"] == "NOT_FOUND"

    def test_start_session_rejects_unknown_override_exercise(self):
        program_id, _ = self.seed_program()
        status, body, _ = self.api.request(
            "POST",
            "/sessions",
            role="USER",
            payload={
                "program_id": str(program_id),
                "exercises": [{
                    "exercise_id": str(ObjectId()),
                    "order": 1,
                    "sets": 3,
                    "reps": 10,
                    "rest_sec": 60,
                }],
            },
        )
        assert status == 400
        assert body["code"] == "BAD_REQUEST"
        assert body["errors"][0]["field"] == "exercises.0.exercise_id"

    def test_finish_session_saves_results_and_duration(self):
        program_id, exercise_id = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        session_id = ObjectId(started["id"])
        self.db.workout_sessions.update_one(
            {"_id": session_id},
            {"$set": {"started_at": datetime.now(UTC) - timedelta(seconds=10)}},
        )

        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{session_id}/finish",
            role="USER",
            payload={
                "exercises": [{
                    "exercise_id": str(exercise_id),
                    "completed_sets": 3,
                    "actual_reps": [10, 10, 9],
                    "is_completed": True,
                    "is_skipped": False,
                }]
            },
        )

        assert status == 200
        assert body["duration_sec"] >= 10
        assert body["exercises"][0]["actual_reps"] == [10, 10, 9]
        assert body["exercises"][0]["is_completed"] is True
        assert "finished_at" in body

    def test_finish_session_cannot_be_repeated(self):
        program_id, exercise_id = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        path = f"/sessions/{started['id']}/finish"
        payload = {
            "exercises": [{
                "exercise_id": str(exercise_id),
                "completed_sets": 0,
                "actual_reps": [],
                "is_completed": False,
                "is_skipped": True,
            }]
        }

        assert self.api.request("POST", path, role="USER", payload=payload)[0] == 200
        status, body, _ = self.api.request("POST", path, role="USER", payload=payload)
        assert status == 409
        assert body["code"] == "CONFLICT"

    def test_history_returns_sessions_newest_first(self):
        program_id, _ = self.seed_program()
        first = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )[1]
        second = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )[1]

        status, body, _ = self.api.request("GET", "/me/sessions", role="USER")
        assert status == 200
        assert [item["id"] for item in body][:2] == [second["id"], first["id"]]

    def test_sessions_require_authentication(self):
        program_id, _ = self.seed_program()
        status, body, _ = self.api.request(
            "POST", "/sessions", role=None, payload={"program_id": str(program_id)}
        )
        assert status == 401
        assert body["code"] == "UNAUTHORIZED"

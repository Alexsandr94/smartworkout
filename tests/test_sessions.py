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

    def seed_program(self, *, author_id=USER_ID, is_public=True, exercises=None):
        if exercises is None:
            exercise_id = self.seed_exercise()
            exercises = [{
                "exercise_id": exercise_id,
                "exercise_name": "Push-ups",
                "order": 1,
                "sets": 3,
                "reps": 10,
                "rest_sec": 60,
            }]
        else:
            exercise_id = exercises[0]["exercise_id"]

        program_id = self.db.programs.insert_one({
            "title": "Test program",
            "description": "",
            "author_id": author_id,
            "is_public": is_public,
            "difficulty": "Beginner",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "exercises": exercises,
        }).inserted_id
        return program_id, exercise_id

    @staticmethod
    def finish_item(started_exercise: dict, **changes):
        item = {
            "exercise_id": started_exercise["exercise_id"],
            "exercise_name": started_exercise["exercise_name"],
            "order": started_exercise["order"],
            "planned_sets": started_exercise["planned_sets"],
            "planned_reps": started_exercise["planned_reps"],
            "rest_sec": started_exercise["rest_sec"],
            "completed_sets": started_exercise["planned_sets"],
            "actual_reps": [started_exercise["planned_reps"]] * started_exercise["planned_sets"],
            "is_completed": True,
            "is_skipped": False,
        }
        item.update(changes)
        return item

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
        assert body["source_program_title"] == "Test program"
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

    def test_start_session_allows_duplicate_exercise_ids_with_unique_order(self):
        exercise_id = self.seed_exercise()
        program_id, _ = self.seed_program(exercises=[{
            "exercise_id": exercise_id,
            "exercise_name": "Push-ups",
            "order": 1,
            "sets": 3,
            "reps": 10,
            "rest_sec": 60,
        }])
        payload = {
            "program_id": str(program_id),
            "exercises": [
                {
                    "exercise_id": str(exercise_id),
                    "order": 1,
                    "sets": 3,
                    "reps": 10,
                    "rest_sec": 60,
                },
                {
                    "exercise_id": str(exercise_id),
                    "order": 2,
                    "sets": 2,
                    "reps": 8,
                    "rest_sec": 30,
                },
            ],
        }

        status, body, _ = self.api.request("POST", "/sessions", role="USER", payload=payload)

        assert status == 201
        assert [item["order"] for item in body["exercises"]] == [1, 2]
        assert body["exercises"][0]["exercise_id"] == body["exercises"][1]["exercise_id"]

    def test_start_session_rejects_duplicate_order(self):
        first_id = self.seed_exercise("First")
        second_id = self.seed_exercise("Second")
        program_id, _ = self.seed_program(exercises=[
            {
                "exercise_id": first_id,
                "exercise_name": "First",
                "order": 1,
                "sets": 3,
                "reps": 10,
                "rest_sec": 60,
            },
            {
                "exercise_id": second_id,
                "exercise_name": "Second",
                "order": 2,
                "sets": 3,
                "reps": 10,
                "rest_sec": 60,
            },
        ])
        payload = {
            "program_id": str(program_id),
            "exercises": [
                {"exercise_id": str(first_id), "order": 1, "sets": 3, "reps": 10, "rest_sec": 60},
                {"exercise_id": str(second_id), "order": 1, "sets": 3, "reps": 10, "rest_sec": 60},
            ],
        }

        status, body, _ = self.api.request("POST", "/sessions", role="USER", payload=payload)

        assert status == 400
        assert any(error["field"] == "exercises.1.order" for error in body["errors"])

    def test_start_session_rejects_exercise_not_in_source_program(self):
        program_id, _ = self.seed_program()
        other_exercise_id = self.seed_exercise("Other")

        status, body, _ = self.api.request(
            "POST",
            "/sessions",
            role="USER",
            payload={
                "program_id": str(program_id),
                "exercises": [{
                    "exercise_id": str(other_exercise_id),
                    "order": 1,
                    "sets": 3,
                    "reps": 10,
                    "rest_sec": 60,
                }],
            },
        )

        assert status == 400
        assert body["errors"][0]["field"] == "exercises.0.exercise_id"

    def test_start_session_rejects_private_foreign_program(self):
        program_id, _ = self.seed_program(author_id=OTHER_USER_ID, is_public=False)
        status, body, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        assert status == 404
        assert body["code"] == "NOT_FOUND"

    def test_finish_session_saves_results_and_duration(self):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        session_id = ObjectId(started["id"])
        self.db.workout_sessions.update_one(
            {"_id": session_id},
            {"$set": {"started_at": datetime.now(UTC) - timedelta(seconds=10)}},
        )

        result = self.finish_item(
            started["exercises"][0],
            actual_reps=[10, 10, 9],
        )
        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{session_id}/finish",
            role="USER",
            payload={"exercises": [result]},
        )

        assert status == 200
        assert body["duration_sec"] >= 10
        assert body["exercises"][0]["actual_reps"] == [10, 10, 9]
        assert body["exercises"][0]["is_completed"] is True
        assert "finished_at" in body

    def test_finish_session_accepts_uppercase_exercise_id(self):
        program_id, _ = self.seed_program()

        _, started, _ = self.api.request(
            "POST",
            "/sessions",
            role="USER",
            payload={"program_id": str(program_id)},
        )

        session_id = ObjectId(started["id"])

        result = self.finish_item(started["exercises"][0])

        original_exercise_id = result["exercise_id"]
        result["exercise_id"] = original_exercise_id.upper()

        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{session_id}/finish",
            role="USER",
            payload={"exercises": [result]},
        )

        assert status == 200
        assert body["exercises"][0]["exercise_id"] == original_exercise_id

        saved_session = self.db.workout_sessions.find_one({"_id": session_id})

        assert isinstance(
            saved_session["exercises"][0]["exercise_id"],
            ObjectId,
        )
        assert (
                saved_session["exercises"][0]["exercise_id"]
                == ObjectId(original_exercise_id)
        )

    @pytest.mark.parametrize("payload", [{}, {"exercises": []}])
    def test_finish_session_requires_at_least_one_exercise(self, payload):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )

        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{started['id']}/finish",
            role="USER",
            payload=payload,
        )

        assert status == 400
        assert body["code"] == "BAD_REQUEST"

    def test_finish_session_rejects_snapshot_mismatch(self):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        result = self.finish_item(started["exercises"][0], exercise_name="Changed")

        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{started['id']}/finish",
            role="USER",
            payload={"exercises": [result]},
        )

        assert status == 400
        assert any(error["field"] == "exercises.0.exercise_name" for error in body["errors"])

    def test_finish_session_distinguishes_duplicate_ids_by_order(self):
        exercise_id = self.seed_exercise()
        program_id, _ = self.seed_program(exercises=[
            {
                "exercise_id": exercise_id,
                "exercise_name": "Push-ups",
                "order": 1,
                "sets": 1,
                "reps": 10,
                "rest_sec": 60,
            },
            {
                "exercise_id": exercise_id,
                "exercise_name": "Push-ups",
                "order": 2,
                "sets": 1,
                "reps": 5,
                "rest_sec": 30,
            },
        ])
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        first = self.finish_item(started["exercises"][0], actual_reps=[9])
        second = self.finish_item(started["exercises"][1], actual_reps=[4])

        status, body, _ = self.api.request(
            "POST",
            f"/sessions/{started['id']}/finish",
            role="USER",
            payload={"exercises": [first, second]},
        )

        assert status == 200
        assert body["exercises"][0]["actual_reps"] == [9]
        assert body["exercises"][1]["actual_reps"] == [4]

    def test_finish_session_cannot_be_repeated(self):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        path = f"/sessions/{started['id']}/finish"
        payload = {"exercises": [self.finish_item(
            started["exercises"][0],
            completed_sets=0,
            actual_reps=[],
            is_completed=False,
            is_skipped=True,
        )]}

        assert self.api.request("POST", path, role="USER", payload=payload)[0] == 200
        status, body, _ = self.api.request("POST", path, role="USER", payload=payload)
        assert status == 409
        assert body["code"] == "CONFLICT"

    def test_history_returns_short_paginated_sessions(self):
        program_id, _ = self.seed_program()
        first = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )[1]
        second = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )[1]

        status, first_page, _ = self.api.request("GET", "/me/sessions?limit=1", role="USER")
        assert status == 200
        assert set(first_page) == {"data", "next", "has_more"}
        assert first_page["has_more"] is True
        assert first_page["data"][0]["id"] == second["id"]
        assert first_page["data"][0]["source_program_title"] == "Test program"
        assert "exercises" not in first_page["data"][0]

        status, second_page, _ = self.api.request(
            "GET",
            f"/me/sessions?limit=1&cursor={first_page['next']}",
            role="USER",
        )
        assert status == 200
        assert second_page["data"][0]["id"] == first["id"]
        assert second_page["has_more"] is False
        assert second_page["next"] is None

    def test_get_single_session_returns_full_snapshot(self):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )

        status, body, _ = self.api.request(
            "GET",
            f"/me/sessions/{started['id']}",
            role="USER",
        )

        assert status == 200
        assert body["id"] == started["id"]
        assert body["source_program_title"] == "Test program"
        assert body["exercises"] == started["exercises"]

    def test_get_single_session_hides_foreign_session(self):
        program_id, _ = self.seed_program()
        _, started, _ = self.api.request(
            "POST", "/sessions", role="USER", payload={"program_id": str(program_id)}
        )
        self.db.workout_sessions.update_one(
            {"_id": ObjectId(started["id"])},
            {"$set": {"user_id": OTHER_USER_ID}},
        )

        status, body, _ = self.api.request(
            "GET",
            f"/me/sessions/{started['id']}",
            role="USER",
        )

        assert status == 404
        assert body["code"] == "NOT_FOUND"

    def test_history_rejects_invalid_pagination(self):
        for query in ("limit=0", "limit=101", "limit=x", "cursor=bad"):
            status, body, _ = self.api.request(
                "GET", f"/me/sessions?{query}", role="USER"
            )
            assert status == 400
            assert body["code"] == "BAD_REQUEST"

    def test_sessions_require_authentication(self):
        program_id, _ = self.seed_program()
        status, body, _ = self.api.request(
            "POST", "/sessions", role=None, payload={"program_id": str(program_id)}
        )
        assert status == 401
        assert body["code"] == "UNAUTHORIZED"

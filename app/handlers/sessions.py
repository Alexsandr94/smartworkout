from datetime import datetime
from http import HTTPStatus

from bson import ObjectId

from app.dependencies import session_service
from app.httpresponse import json_response
from app.middlewares.auth import require_auth
from app.routing import router


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, list):
        return [_serialize_value(item) for item in value]

    if isinstance(value, dict):
        return {
            key: _serialize_value(item)
            for key, item in value.items()
        }

    return value


def _serialize_session(session: dict) -> dict:
    data = _serialize_value(session)

    data["id"] = data.pop("_id")

    return data


@router.get("/me/sessions", middlewares=[require_auth])
def get_my_sessions(request):
    user_id = request["user"]["id"]

    sessions = session_service.get_user_sessions(user_id)

    return json_response(
        [_serialize_session(session) for session in sessions],
        HTTPStatus.OK,
    )
from datetime import UTC, datetime
from http import HTTPStatus

from bson import ObjectId

from app.dependencies import session_service
from app.dtos.base import DTOValidationError
from app.dtos.session import SessionFinishDTO, SessionListDTO, SessionStartDTO
from app.errors.http import bad_request
from app.httpresponse import Response, error_response, json_response
from app.middlewares.auth import require_auth
from app.routing import router


def _serialize_value(value):
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="milliseconds")

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


def _validation_response(exc: DTOValidationError) -> Response:
    payload, status = bad_request(exc.errors)
    return error_response(payload, status)


@router.get("/me/sessions", middlewares=[require_auth])
def get_my_sessions(request):
    try:
        filters = SessionListDTO.from_dict(request.get("query") or {})
    except DTOValidationError as exc:
        return _validation_response(exc)

    page = session_service.get_user_sessions(
        request["user"]["id"],
        filters.pagination,
    )
    return json_response(
        {
            "data": [_serialize_session(session) for session in page.data],
            "next": page.next,
            "has_more": page.has_more,
        },
        HTTPStatus.OK,
    )


@router.get("/me/sessions/{session_id}", middlewares=[require_auth])
def get_my_session(request):
    session = session_service.get_user_session(
        request["user"]["id"],
        request["params"]["session_id"],
    )
    return json_response(_serialize_session(session), HTTPStatus.OK)


@router.post("/sessions", middlewares=[require_auth])
def start_session(request):
    try:
        dto = SessionStartDTO.from_dict(request.get("body"))
        session = session_service.start_session(
            user_id=request["user"]["id"],
            program_id=dto.program_id,
            exercises=dto.exercises_document(),
        )
    except DTOValidationError as exc:
        return _validation_response(exc)

    return json_response(_serialize_session(session), HTTPStatus.CREATED)


@router.post("/sessions/{session_id}/finish", middlewares=[require_auth])
def finish_session(request):
    try:
        dto = SessionFinishDTO.from_dict(request.get("body") or {})
        session = session_service.finish_session(
            user_id=request["user"]["id"],
            session_id=request["params"]["session_id"],
            results=dto.exercises_document(),
        )
    except DTOValidationError as exc:
        return _validation_response(exc)

    return json_response(_serialize_session(session), HTTPStatus.OK)

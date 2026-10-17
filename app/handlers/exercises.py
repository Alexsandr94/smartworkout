from dataclasses import fields
from datetime import UTC
from http import HTTPStatus

from app.dependencies import exercise_service
from app.dtos.base import DTOValidationError
from app.dtos.exercises import UNSET, ExerciseCreateDTO, ExerciseListDTO, ExerciseUpdateDTO, validate_exercise_id
from app.errors.exercises import ExerciseNotFoundError
from app.errors.http import bad_request
from app.httpresponse import Response, error_response, json_response
from app.middlewares.auth import require_admin, require_auth
from app.routing import router


def serialize_exercise(document: dict) -> dict:
    created_at = document.get('created_at')
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    result = {
        'id': str(document.get('_id')),
        'name': document.get('name'),
        'muscle_groups': document.get('muscle_groups'),
        'equipment': document.get('equipment'),
        'created_at': created_at.astimezone(UTC).isoformat(timespec='milliseconds'),
    }
    for name in ('description', 'video_url', 'image_url'):
        if name in document:
            result[name] = document.get(name)
    return result


def _body_document(request: dict, dto_type) -> dict:
    body = request.get('body')
    if not isinstance(body, dict):
        raise DTOValidationError([{'field': 'body', 'message': 'body must be a JSON object'}])
    values = {item.name: body.get(item.name, UNSET) for item in fields(dto_type)}
    return dto_type(**values).to_document()


def _validation_response(exc: DTOValidationError) -> Response:
    payload, status = bad_request(exc.errors)
    return error_response(payload, status)


def _existing_id(params: dict):
    try:
        return validate_exercise_id(params.get('exercise_id'))
    except DTOValidationError:
        raise ExerciseNotFoundError() from None


@router.get('/exercises', [require_auth])
def list_exercises(request):
    query = request.get('query') or {}
    try:
        filters = ExerciseListDTO(
            muscle_group=query.get('muscle_group'), equipment=query.get('equipment'),
            search=query.get('search'), cursor=query.get('cursor'), limit=query.get('limit', 20),
        )
    except DTOValidationError as exc:
        return _validation_response(exc)
    result = exercise_service.list(filters)
    return json_response({**result, 'data': [serialize_exercise(doc) for doc in result.get('data')]})


@router.get('/exercises/{exercise_id}', [require_auth])
def get_exercise(request):
    document = exercise_service.get(_existing_id(request.get('params') or {}))
    return json_response(serialize_exercise(document))


@router.post('/exercises', [require_auth, require_admin])
def create_exercise(request):
    try:
        values = _body_document(request, ExerciseCreateDTO)
    except DTOValidationError as exc:
        return _validation_response(exc)
    document = exercise_service.create(values)
    return json_response(serialize_exercise(document), HTTPStatus.CREATED)


@router.put('/exercises/{exercise_id}', [require_auth, require_admin])
def update_exercise(request):
    params = request.get('params') or {}
    try:
        exercise_id = validate_exercise_id(params.get('exercise_id'))
        changes = _body_document(request, ExerciseUpdateDTO)
    except DTOValidationError as exc:
        return _validation_response(exc)
    document = exercise_service.update(exercise_id, changes)
    return json_response(serialize_exercise(document))


@router.delete('/exercises/{exercise_id}', [require_auth, require_admin])
def delete_exercise(request):
    exercise_service.delete(_existing_id(request.get('params') or {}))
    return Response(HTTPStatus.NO_CONTENT)

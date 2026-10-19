from datetime import UTC
from http import HTTPStatus

from app.dependencies import exercise_service
from app.dtos.base import DTOValidationError
from app.dtos.exercises import ExerciseCreateDTO, ExerciseListDTO, ExerciseUpdateDTO
from app.dtos.utils import validate_object_id
from app.errors.exercises import ExerciseNotFoundError
from app.errors.http import bad_request
from app.httpresponse import Response, error_response, json_response
from app.middlewares.auth import require_admin, require_auth
from app.models.exercise import Exercise
from app.routing import router


def serialize_exercise(exercise: Exercise) -> dict:
    created_at = exercise.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    result = {
        'id': str(exercise.id), 'name': exercise.name,
        'muscle_groups': exercise.muscle_groups, 'equipment': exercise.equipment,
        'created_at': created_at.astimezone(UTC).isoformat(timespec='milliseconds'),
    }
    for name in ('description', 'video_url', 'image_url'):
        value = getattr(exercise, name)
        if value is not None:
            result[name] = value
    return result


def _validation_response(exc: DTOValidationError) -> Response:
    payload, status = bad_request(exc.errors)
    return error_response(payload, status)


def _exercise_id(request: dict):
    params = request.get('params') or {}
    return validate_object_id(params.get('exercise_id'), 'exercise_id')


def _existing_id(request: dict):
    try:
        return _exercise_id(request)
    except DTOValidationError:
        raise ExerciseNotFoundError() from None


@router.get('/exercises', [require_auth])
def list_exercises(request):
    try:
        filters = ExerciseListDTO.from_dict(request.get('query') or {})
    except DTOValidationError as exc:
        return _validation_response(exc)
    page = exercise_service.list(
        muscle_groups=filters.muscle_group.split(',') if filters.muscle_group is not None else None,
        equipment=filters.equipment.split(',') if filters.equipment is not None else None,
        search=filters.search, pagination=filters.pagination,
    )
    return json_response({
        'data': [serialize_exercise(exercise) for exercise in page.data],
        'next': page.next, 'has_more': page.has_more,
    })


@router.get('/exercises/{exercise_id}', [require_auth])
def get_exercise(request):
    return json_response(serialize_exercise(exercise_service.get(_existing_id(request))))


@router.post('/exercises', [require_auth, require_admin])
def create_exercise(request):
    try:
        values = ExerciseCreateDTO.from_dict(request.get('body')).to_document()
    except DTOValidationError as exc:
        return _validation_response(exc)
    exercise = exercise_service.create(values)
    return json_response(serialize_exercise(exercise), HTTPStatus.CREATED)


@router.put('/exercises/{exercise_id}', [require_auth, require_admin])
def update_exercise(request):
    try:
        exercise_id = _exercise_id(request)
        changes = ExerciseUpdateDTO.from_dict(request.get('body')).to_document()
    except DTOValidationError as exc:
        return _validation_response(exc)
    return json_response(serialize_exercise(exercise_service.update(exercise_id, changes)))


@router.delete('/exercises/{exercise_id}', [require_auth, require_admin])
def delete_exercise(request):
    exercise_service.delete(_existing_id(request))
    return Response(HTTPStatus.NO_CONTENT)

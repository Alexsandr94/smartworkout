from http import HTTPStatus
from app.dependencies import program_service
from app.dtos.program import ProgramCreateDTO, ProgramUpdateDTO
from app.dtos.base import DTOValidationError
from app.httpresponse import json_response, error_response, Response
from app.routing import router
from app.middlewares.auth import require_auth


def _serialize_program(program: dict) -> dict:
    return {
        "id": str(program["_id"]),
        "title": program["title"],
        "description": program["description"],
        "is_public": program["is_public"],
        "difficulty": program["difficulty"],
        "author_id": str(program["author_id"]),
        "exercises": [
            {
                "exercise_id": str(ex["exercise_id"]),
                "exercise_name": ex["exercise_name"],
                "order": ex["order"],
                "sets": ex["sets"],
                "reps": ex["reps"],
                "rest_sec": ex["rest_sec"]
            } for ex in program["exercises"]
        ],
        "created_at": program["created_at"].isoformat(),
        "updated_at": program["updated_at"].isoformat()
    }

@router.post("/programs", middlewares=(require_auth,))
def create_program(request):
    try:
        dto = ProgramCreateDTO.from_dict(request.get("body"))
    except DTOValidationError as exc:
        return error_response(
            {"code": "BAD_REQUEST", "message": "Validation failed", "errors": exc.errors},
            HTTPStatus.BAD_REQUEST,
        )

    author_id = request["user"]["id"]
    data = dto.to_document()

    try:
        program = program_service.create(data, author_id)
    except DTOValidationError as exc:
        return error_response(
            {"code": "BAD_REQUEST", "message": "Validation failed", "errors": exc.errors},
            HTTPStatus.BAD_REQUEST,
        )

    return json_response(_serialize_program(program), HTTPStatus.CREATED)

@router.get("/programs", middlewares=(require_auth,))
def get_programs(request):
    user_id = request["user"]["id"]
    programs = program_service.get_all(user_id)
    return json_response([_serialize_program(p) for p in programs], HTTPStatus.OK)


@router.get("/programs/{id}", middlewares=(require_auth,))
def get_program_by_id(request):
    user_id = request["user"]["id"]
    program_id = request["params"]["id"]
    program = program_service.get_by_id(program_id, user_id)
    return json_response(_serialize_program(program), HTTPStatus.OK)


@router.patch("/programs/{id}", middlewares=(require_auth,))
def update_program(request):
    program_id = request["params"]["id"]
    user_id = request["user"]["id"]

    try:
        dto = ProgramUpdateDTO.from_dict(request.get("body"))
    except DTOValidationError as exc:
        return error_response(
            {"code": "BAD_REQUEST", "message": "Validation failed", "errors": exc.errors},
            HTTPStatus.BAD_REQUEST,
        )

    data = dto.to_document()

    try:
        program = program_service.update(program_id, data, user_id)
    except DTOValidationError as exc:
        return error_response(
            {"code": "BAD_REQUEST", "message": "Validation failed", "errors": exc.errors},
            HTTPStatus.BAD_REQUEST,
        )

    return json_response(_serialize_program(program), HTTPStatus.OK)

@router.delete("/programs/{id}", middlewares=(require_auth,))
def delete_program(request):
    program_id = request["params"]["id"]
    user_id = request["user"]["id"]

    program_service.delete(program_id, user_id)
    return Response(status=HTTPStatus.NO_CONTENT)
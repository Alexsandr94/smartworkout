from http import HTTPStatus
from app.core.cookies import build_refresh_cookie, clear_refresh_cookie
from app.dependencies import auth_service
from app.dtos.auth import LoginDTO, RegisterDTO
from app.dtos.base import DTOValidationError
from app.errors.auth import AuthorizationRequiredError
from app.httpresponse import Response, error_response, json_response
from app.routing import router

@router.post("/auth/register")
def register(request):
    try:
        dto = RegisterDTO.from_dict(request.get("body"))
    except DTOValidationError as exc:
        return error_response(
            {
                "code": "BAD_REQUEST",
                "message": "Validation failed",
                "errors": exc.errors,
            },
            HTTPStatus.BAD_REQUEST,
        )

    user = auth_service.register(
        dto.email,
        dto.password,
    )

    return json_response(
        {
            "id": str(user["_id"]),
            "email": user["email"],
            "created_at": user["created_at"].isoformat(),
        },
        HTTPStatus.CREATED,
    )

@router.post("/auth/login")
def login(request):
    try:
        dto = LoginDTO.from_dict(request.get("body"))
    except DTOValidationError as exc:
        return error_response(
            {
                "code": "BAD_REQUEST",
                "message": "Validation failed",
                "errors": exc.errors,
            },
            HTTPStatus.BAD_REQUEST,
        )

    result = auth_service.login(
        dto.email,
        dto.password,
    )

    set_cookie = build_refresh_cookie(
        result["refresh_token"],
        max_age=result["refresh_ttl"]
    )

    return json_response(
        {
            "access_token": result["access_token"],
            "user": {
                "id": str(result["user"]["_id"]),
                "email": result["user"]["email"],
            },
        },
        HTTPStatus.OK,
        headers=[
            ("Set-Cookie", set_cookie),
        ],
    )

@router.post("/auth/refresh")
def refresh(request):
    refresh_token = request["cookies"].get("refresh_token")

    if not refresh_token:
        raise AuthorizationRequiredError("refresh token is required")

    result = auth_service.refresh(refresh_token)

    return json_response(
        {
            "access_token": result["access_token"],
        },
        HTTPStatus.OK,
        headers=[
            (
                "Set-Cookie",
                build_refresh_cookie(
                    result["refresh_token"],
                    result["refresh_ttl"],
                ),
            ),
        ],
    )


@router.post("/auth/logout")
def logout(request):
    return Response(
        status=HTTPStatus.NO_CONTENT,
        headers=[
            ("Set-Cookie", clear_refresh_cookie()),
        ],
    )
import logging
from http import HTTPStatus

from app.errors.base import AppError
from app.httpresponse import error_response

log = logging.getLogger(__name__)


def exception_middleware(request, next_handler):
    try:
        return next_handler(request)

    except AppError as exc:
        return error_response(
            {
                "code": exc.code,
                "message": exc.message,
            },
            exc.status,
        )

    except Exception:
        log.exception(
            "Unhandled exception during request",
            extra={
                "method": request["method"],
                "path": request["path"],
                "status": int(HTTPStatus.INTERNAL_SERVER_ERROR),
            },
        )

        return error_response(
            {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
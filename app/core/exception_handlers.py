from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_codes import ErrorCodes
from app.core.exceptions import AppException
from app.core.logger import get_logger
from app.core.responses import error

logger = get_logger("exception_handlers.py")

_STATUS_TO_ERROR_CODE = {
    400: ErrorCodes.BAD_REQUEST,
    403: ErrorCodes.FORBIDDEN,
    404: ErrorCodes.NOT_FOUND,
    409: ErrorCodes.CONFLICT,
    422: ErrorCodes.INVALID_PARAMS,
    429: ErrorCodes.TOO_MANY_REQUESTS,
    503: ErrorCodes.SERVICE_UNAVAILABLE,
    500: ErrorCodes.INTERNAL_SERVER_ERROR,
}


def _build_error_response(
    err_code: str,
    err_message: str,
    http_status: int,
) -> JSONResponse:
    payload = error(
        err_code=err_code,
        err_message=err_message,
        http_status=http_status,
    )
    return JSONResponse(
        status_code=http_status,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ):
        logger.error(f"AppException [{exc.err_code}]: {exc.message}")
        return _build_error_response(
            err_code=exc.err_code,
            err_message=exc.message,
            http_status=exc.status_code,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        detail = exc.detail
        if isinstance(detail, dict):
            err_message = detail.get(
                "errMessage",
                detail.get("message", str(detail)),
            )
            err_code = detail.get(
                "errCode",
                _STATUS_TO_ERROR_CODE.get(
                    exc.status_code,
                    ErrorCodes.BAD_REQUEST,
                ),
            )
        else:
            err_message = str(detail)
            err_code = _STATUS_TO_ERROR_CODE.get(
                exc.status_code,
                ErrorCodes.BAD_REQUEST,
            )

        return _build_error_response(
            err_code=err_code,
            err_message=err_message,
            http_status=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        logger.error(f"Validation error: {exc.errors()}")
        return _build_error_response(
            err_code=ErrorCodes.INVALID_PARAMS,
            err_message="Request validation failed",
            http_status=422,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ):
        logger.error(f"Unhandled exception: {str(exc)}")
        return _build_error_response(
            err_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            err_message="Internal server error",
            http_status=500,
        )

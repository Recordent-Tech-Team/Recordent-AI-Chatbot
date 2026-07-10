class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        err_code: str | None = None,
    ):
        from app.core.error_codes import ErrorCodes

        self.message = message
        self.status_code = status_code
        self.err_code = err_code or ErrorCodes.BAD_REQUEST
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        from app.core.error_codes import ErrorCodes

        super().__init__(
            message,
            status_code=404,
            err_code=ErrorCodes.NOT_FOUND,
        )


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized access"):
        from app.core.error_codes import ErrorCodes

        super().__init__(
            message,
            status_code=403,
            err_code=ErrorCodes.UNAUTHORIZED,
        )


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed"):
        from app.core.error_codes import ErrorCodes

        super().__init__(
            message,
            status_code=422,
            err_code=ErrorCodes.INVALID_PARAMS,
        )


class ConflictError(AppException):
    def __init__(self, message: str = "Conflict"):
        from app.core.error_codes import ErrorCodes

        super().__init__(
            message,
            status_code=409,
            err_code=ErrorCodes.CONFLICT,
        )

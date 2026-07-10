from app.core.error_codes import ErrorCodes
from app.core.exceptions import AppException

_AWS_AUTH_ERROR_MARKERS = (
    "token has expired and refresh failed",
    "error when retrieving token from sso",
    "tokenretrievalerror",
    "expiredtoken",
    "expiredtokenexception",
    "invalidclienttokenid",
    "unrecognizedclientexception",
    "nocredentialserror",
    "unable to locate credentials",
)


def is_aws_auth_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(marker in message for marker in _AWS_AUTH_ERROR_MARKERS)


def to_aws_auth_app_exception(
    error: Exception,
    service_name: str,
    operation: str,
) -> AppException | None:
    if not is_aws_auth_error(error):
        return None

    return AppException(
        message=(
            "AWS credentials are unavailable or expired while calling "
            f"{service_name} {operation}. "
            "If using AWS SSO, run `aws sso login --profile <your-profile>` "
            "and retry."
        ),
        status_code=503,
        err_code=ErrorCodes.SERVICE_UNAVAILABLE,
    )

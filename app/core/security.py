from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.error_codes import ErrorCodes
from app.core.logger import get_logger

logger = get_logger("security.py")

CHAT_API_KEY_NAME = "X-API-SECRET"
ADMIN_API_KEY_NAME = "X-ADMIN-SECRET"

chat_api_key_header = APIKeyHeader(
    name=CHAT_API_KEY_NAME,
    auto_error=False,
)
admin_api_key_header = APIKeyHeader(
    name=ADMIN_API_KEY_NAME,
    auto_error=False,
)


def _validate_secret(
    provided_key: str | None,
    expected_key: str,
    label: str,
) -> None:
    if not provided_key or provided_key != expected_key:
        logger.error(f"Unauthorized {label} access attempted")
        raise HTTPException(
            status_code=403,
            detail={
                "errCode": ErrorCodes.UNAUTHORIZED,
                "errMessage": "Unauthorized access.",
            },
        )


def verify_chat_api_secret(
    api_key: str | None = Depends(chat_api_key_header),
) -> None:
    _validate_secret(api_key, settings.CHAT_API_SECRET, "chat API")


def verify_admin_api_secret(
    api_key: str | None = Depends(admin_api_key_header),
) -> None:
    _validate_secret(api_key, settings.ADMIN_API_SECRET, "admin API")

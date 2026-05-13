from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.logger import get_logger
logger = get_logger("security.py")

API_KEY_NAME = "x-recordent-key"
api_key_header = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False
)

def verify_api_key(
    api_key: str = Depends(api_key_header)
):
    try:
        if (
            not api_key
            or
            api_key != settings.RECORDENT_BACKEND_KEY
        ):
            logger.error("Unauthorized API access attempted")
            raise HTTPException(
                status_code=403,
                detail={
                    "status": False,
                    "message": "Unauthorized access."
                }
            )

    except HTTPException:
        raise
    except Exception as error:
        logger.error(f"Error during API key validation: {str(error)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": False,
                "message": "Internal server error"
            }
        )
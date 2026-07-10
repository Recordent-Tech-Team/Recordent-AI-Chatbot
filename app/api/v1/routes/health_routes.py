from app.core.logger import get_logger
from app.core.responses import success
from app.core.security import verify_admin_api_secret
from app.services.health.health_service import get_health_check_data
from fastapi import APIRouter, Depends

logger = get_logger("health_routes.py")

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    return success(
        message="Application is running successfully",
        data=None,
        http_status=200,
    )


@router.get("/health-check", dependencies=[Depends(verify_admin_api_secret)])
async def health_check():
    health_data = await get_health_check_data()
    http_status = 200 if health_data["isHealthy"] else 503
    return success(
        message="Success",
        data=health_data,
        http_status=http_status,
    )

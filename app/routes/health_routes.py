from fastapi import APIRouter
from app.core.logger import get_logger
router = APIRouter()
logger = get_logger("health_routes.py")

@router.get("/")
async def health_check():
    return {
        "status": True,
        "message": "Application is running successfully"
    }
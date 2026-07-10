import time
from datetime import datetime, timezone

from sqlalchemy import text

from app.core.config import settings
from app.core.logger import get_logger
from app.db.session import engine

logger = get_logger("health_service.py")

SERVICE_STARTED_AT: datetime | None = None


def set_service_started_at(started_at: datetime) -> None:
    global SERVICE_STARTED_AT
    SERVICE_STARTED_AT = started_at


def get_service_started_at() -> datetime:
    if SERVICE_STARTED_AT is None:
        return datetime.now(timezone.utc)
    return SERVICE_STARTED_AT


async def _check_database() -> dict:
    start = time.perf_counter()
    is_up = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        is_up = True
    except Exception as error:
        logger.error(f"Database health check failed: {error}")

    latency_ms = int((time.perf_counter() - start) * 1000)
    return {
        "name": "database",
        "status": "up" if is_up else "down",
        "latencyMs": latency_ms,
    }


async def get_health_check_data() -> dict:
    now = datetime.now(timezone.utc)
    started_at = get_service_started_at()
    dependencies = [await _check_database()]

    up_count = sum(
        1 for dep in dependencies if dep["status"] == "up"
    )
    down_count = len(dependencies) - up_count
    is_healthy = down_count == 0

    return {
        "isHealthy": is_healthy,
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV.upper(),
        "checkedAt": now.strftime("%Y-%m-%d %H:%M:%S"),
        "serviceStartedAt": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "uptimeSeconds": int((now - started_at).total_seconds()),
        "recentDowntimeLikely": down_count > 0,
        "dependencies": dependencies,
        "dependenciesSummary": {
            "total": len(dependencies),
            "up": up_count,
            "down": down_count,
        },
    }

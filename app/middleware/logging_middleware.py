import time

from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        access_logger = logger.bind(module="access")
        app_logger = logger.bind(module="logging_middleware.py")
        try:
            response = await call_next(request)
            process_time = round(
                (time.time() - start_time) * 1000,
                2,
            )
            access_logger.info(
                f"{request.method} "
                f"{request.url.path} "
                f"STATUS:{response.status_code} "
                f"TIME:{process_time}ms"
            )
            return response

        except Exception as exc:
            process_time = round(
                (time.time() - start_time) * 1000,
                2,
            )
            access_logger.info(
                f"{request.method} "
                f"{request.url.path} "
                f"STATUS:500 "
                f"TIME:{process_time}ms"
            )
            app_logger.error(
                f"Unhandled request exception: "
                f"{request.method} {request.url.path} "
                f"ERROR:{str(exc)}"
                f" TIME:{process_time}ms"
            )
            raise

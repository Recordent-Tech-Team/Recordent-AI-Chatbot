import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.error_codes import ErrorCodes
from app.core.logger import get_logger
from app.core.responses import error

logger = get_logger("response_middleware.py")


class ResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as error:
            logger.error(f"Response JSON decode failed: {error}")
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        if not isinstance(payload, dict) or "httpStatus" not in payload:
            if isinstance(payload, dict) and payload.get("data") is None:
                payload.pop("data", None)
            return JSONResponse(
                status_code=response.status_code,
                content=payload,
            )

        status_code = int(payload.pop("httpStatus"))
        if payload.get("data") is None:
            payload.pop("data", None)
        headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower() != "content-length"
        }

        return JSONResponse(
            status_code=status_code,
            content=payload,
            headers=headers,
        )

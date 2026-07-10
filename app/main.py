from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi import Response

from app.api.v1.routes.admin_routes import router as admin_router
from app.api.v1.routes.chat_routes import router as chat_router
from app.api.v1.routes.health_routes import router as health_router
from app.clients.aws_session import get_aioboto3_session
from app.core.config import settings
from app.core.error_codes import ErrorCodes
from app.core.exceptions import AppException
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import get_logger
from app.db.session import check_db_connection
from app.db.session import dispose_engine
from app.middleware.cors_middleware import setup_cors
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.response_middleware import ResponseMiddleware
from app.services.bedrock.chat_service import BedrockChatService
from app.services.bedrock.embedding_service import BedrockEmbeddingService
from app.services.health.health_service import set_service_started_at

logger = get_logger("main.py")


def _validate_bedrock_model_ids() -> None:
    chat_model_id = (settings.BEDROCK_CHAT_MODEL_ID or "").strip()
    embedding_model_id = (settings.BEDROCK_EMBEDDING_MODEL_ID or "").strip()
    if not chat_model_id or not embedding_model_id:
        raise AppException(
            message=(
                "Missing required Bedrock model configuration. "
                "Both BEDROCK_CHAT_MODEL_ID and "
                "BEDROCK_EMBEDDING_MODEL_ID must be set."
            ),
            status_code=500,
            err_code=ErrorCodes.INTERNAL_SERVER_ERROR,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_service_started_at(datetime.now(timezone.utc))
    logger.info("Application started")
    _validate_bedrock_model_ids()
    db_connected = await check_db_connection()
    if db_connected:
        logger.info("Database connection established")
    else:
        logger.error("Database connection failed at startup")

    aws_session = get_aioboto3_session()
    chat_service = BedrockChatService(aws_session)
    embedding_service = BedrockEmbeddingService(aws_session)
    await chat_service.validate_model()
    await embedding_service.validate_model()
    yield
    await dispose_engine()


app = FastAPI(
    title="Recordent AI Chatbot",
    lifespan=lifespan,
)

app.add_middleware(LoggingMiddleware)
setup_cors(app)
app.add_middleware(ResponseMiddleware)
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)

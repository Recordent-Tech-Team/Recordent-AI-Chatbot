from fastapi import FastAPI
from app.routes.health_routes import (router as health_router)
from app.routes.chatbot_routes import (router as chatbot_router)
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.cors_middleware import setup_cors
from app.core.logger import get_logger
logger = get_logger("main.py")

app = FastAPI(title="Recordent AI Chatbot")
app.add_middleware(LoggingMiddleware)
setup_cors(app)

app.include_router(health_router)
app.include_router(chatbot_router)

logger.info("Application started")

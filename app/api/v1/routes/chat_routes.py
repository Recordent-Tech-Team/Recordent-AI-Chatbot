from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_chat_service
from app.core.logger import get_logger
from app.core.responses import success
from app.core.security import verify_chat_api_secret
from app.schemas.chat import (
    ChatMessageRequest,
    CloseSessionRequest,
)
from app.services.chat.chat_service import ChatService

logger = get_logger("chat_routes.py")

router = APIRouter(
    prefix="/v1/chat",
    tags=["Chat"],
    dependencies=[Depends(verify_chat_api_secret)],
)


@router.post("/create-session")
async def create_session(
    chat_service: ChatService = Depends(get_chat_service),
):
    session_id = await chat_service.create_session()
    return success(
        message="Success",
        data={"session_id": str(session_id)},
        http_status=201,
    )


@router.post("/send-message")
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    result = await chat_service.process_message(
        request.session_id,
        request.message,
    )
    return success(
        message="Success",
        data=result,
        http_status=200,
    )


@router.post("/close-session")
async def close_session(
    request: CloseSessionRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    await chat_service.close_session(request.session_id)
    return success(
        message="Success",
        data={
            "session_id": str(request.session_id),
            "status": "closed",
        },
        http_status=200,
    )

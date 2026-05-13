from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.core.logger import get_logger
from app.core.security import verify_api_key
from app.services.ingestion.ingestion_service import build_index
from app.services.chatbot.chatbot_service import start_chat

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot"]
)

logger = get_logger("chatbot_routes.py")
class ChatRequest(BaseModel):
    question: str


@router.post(
    "/buildTokens",
    dependencies=[Depends(verify_api_key)]
)
async def build_tokens(
    force: bool = Query(False)
):
    logger.info("Build tokens API called")
    try:
        return build_index(
            force_rebuild=force
        )
    
    except Exception as error:
        logger.error(
            f"Build tokens failed: {str(error)}"
        )
        return {
            "status": False,
            "message": "Failed to build tokens"
        }


@router.post(
    "/startConversation",
    dependencies=[Depends(verify_api_key)]
)
async def start_conversation(
    request: ChatRequest
):
    try:
        return start_chat(
            request.question
        )
    
    except Exception as error:
        logger.error(
            f"Conversation failed: {str(error)}"
        )
        return {
            "status": False,
            "message": "Chat processing failed"
        }
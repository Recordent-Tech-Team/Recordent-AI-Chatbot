import time
import uuid

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.db.models import SessionStatus
from app.db.repositories import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from app.services.bedrock.chat_service import BedrockChatService
from app.services.evaluation.evaluation_service import EvaluationService
from app.services.retrieval.retrieval_service import RetrievalService

logger = get_logger("chat_service.py")


class ChatService:
    def __init__(
        self,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
        retrieval_service: RetrievalService,
        chat_service: BedrockChatService,
        evaluation_service: EvaluationService,
    ):
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.retrieval_service = retrieval_service
        self.chat_service = chat_service
        self.evaluation_service = evaluation_service

    async def create_session(self) -> uuid.UUID:
        session = await self.session_repo.create()
        return session.uuid

    async def close_session(self, session_uuid: uuid.UUID) -> None:
        session = await self.session_repo.get_by_uuid(session_uuid)
        if not session:
            raise NotFoundError("Session not found")
        if session.status == SessionStatus.CLOSED:
            raise ValidationError("Session is already closed")
        await self.session_repo.close(session)

    async def process_message(
        self,
        session_uuid: uuid.UUID,
        message: str,
    ) -> dict:
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")

        session = await self.session_repo.get_by_uuid(session_uuid)
        if not session:
            raise NotFoundError("Session not found")
        if session.status == SessionStatus.CLOSED:
            raise ValidationError("Session is closed")

        start_time = time.perf_counter()

        history_messages = await self.message_repo.get_recent_by_session(
            session.id,
            settings.CHAT_MAX_HISTORY_MESSAGES,
        )
        history = []
        for msg in history_messages:
            history.append({
                "role": "user",
                "content": msg.message,
            })
            if msg.response:
                history.append({
                    "role": "assistant",
                    "content": msg.response,
                })

        retrieved = await self.retrieval_service.retrieve(message)
        context_chunks = [chunk for chunk, _ in retrieved]
        context = "\n\n".join(context_chunks)

        chat_result = await self.chat_service.generate(
            context=context,
            question=message,
            history=history,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        await self.message_repo.create(
            session_id=session.id,
            role="user",
            message=message,
            response=chat_result.answer,
            response_time_ms=elapsed_ms,
        )

        if settings.CHAT_EVALUATION_ENABLED:
            await self.evaluation_service.evaluate(
                session_id=session.id,
                question=message,
                retrieved_chunks=context_chunks,
                answer=chat_result.answer,
                latency_ms=elapsed_ms,
                token_usage={
                    "input_tokens": chat_result.input_tokens,
                    "output_tokens": chat_result.output_tokens,
                },
                retrieval_scores=[score for _, score in retrieved],
                context=context,
            )

        return {
            "session_id": str(session_uuid),
            "response": chat_result.answer,
            "response_time_ms": elapsed_ms,
        }

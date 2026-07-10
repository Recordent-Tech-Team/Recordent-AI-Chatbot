import asyncio

from app.core.logger import get_logger
from app.db.repositories import EvaluationLogRepository
from app.services.bedrock.chat_service import BedrockChatService

logger = get_logger("evaluation_service.py")


class EvaluationService:
    def __init__(
        self,
        evaluation_repo: EvaluationLogRepository,
        chat_service: BedrockChatService,
    ):
        self.evaluation_repo = evaluation_repo
        self.chat_service = chat_service

    async def evaluate(
        self,
        session_id: int | None,
        question: str,
        retrieved_chunks: list[str],
        answer: str,
        latency_ms: int,
        token_usage: dict,
        retrieval_scores: list[float],
        context: str,
    ) -> None:
        retrieval_score = (
            sum(retrieval_scores) / len(retrieval_scores)
            if retrieval_scores
            else 0.0
        )

        grounding_score, quality_score = await asyncio.gather(
            self._score_grounding(context, answer),
            self._score_quality(question, answer),
        )

        await self.evaluation_repo.create(
            session_id=session_id,
            question=question,
            retrieved_chunks=retrieved_chunks,
            answer=answer,
            latency_ms=latency_ms,
            token_usage=token_usage,
            retrieval_score=round(retrieval_score, 4),
            grounding_score=round(grounding_score, 4),
            quality_score=round(quality_score, 4),
        )

    async def _score_grounding(
        self,
        context: str,
        answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 how well the answer uses ONLY the provided context.
Return only a decimal number between 0.0 and 1.0.

CONTEXT:
{context}

ANSWER:
{answer}
"""
        return await self.chat_service.judge_score(prompt)

    async def _score_quality(
        self,
        question: str,
        answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 the relevance and completeness of the answer to the question.
Return only a decimal number between 0.0 and 1.0.

QUESTION:
{question}

ANSWER:
{answer}
"""
        return await self.chat_service.judge_score(prompt)

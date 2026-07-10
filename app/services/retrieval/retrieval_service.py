from app.core.config import settings
from app.core.logger import get_logger
from app.db.repositories import EmbeddingRepository
from app.services.bedrock.embedding_service import BedrockEmbeddingService

logger = get_logger("retrieval_service.py")


class RetrievalService:
    def __init__(
        self,
        embedding_repo: EmbeddingRepository,
        embedding_service: BedrockEmbeddingService,
    ):
        self.embedding_repo = embedding_repo
        self.embedding_service = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        if not query:
            logger.error("Empty query received")
            return []

        k = top_k or settings.RAG_TOP_K
        query_embedding = await self.embedding_service.embed_text(query)
        results = await self.embedding_repo.search_active(
            query_embedding,
            k,
        )
        return [(chunk_text, score) for chunk_text, _, score in results]

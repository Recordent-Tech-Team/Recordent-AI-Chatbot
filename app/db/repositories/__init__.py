import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    ChatMessage,
    ChatSession,
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    Embedding,
    EmbeddingArchive,
    EvaluationLog,
    SessionStatus,
)


class ChatSessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self) -> ChatSession:
        session = ChatSession(status=SessionStatus.ACTIVE)
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_uuid(self, session_uuid: uuid.UUID) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.uuid == session_uuid,
                ChatSession.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def close(self, session: ChatSession) -> ChatSession:
        session.status = SessionStatus.CLOSED
        session.closed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return session

    async def list_paginated(
        self,
        page: int,
        size: int,
    ) -> tuple[list[ChatSession], int]:
        offset = (page - 1) * size
        count_result = await self.db.execute(
            select(func.count()).select_from(ChatSession).where(
                ChatSession.deleted_at.is_(None)
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.deleted_at.is_(None))
            .order_by(ChatSession.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        return list(result.scalars().all()), total

    async def count_all(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ChatSession).where(
                ChatSession.deleted_at.is_(None)
            )
        )
        return result.scalar_one()


class ChatMessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: int,
        role: str,
        message: str,
        response: str | None = None,
        response_time_ms: int | None = None,
    ) -> ChatMessage:
        chat_message = ChatMessage(
            session_id=session_id,
            role=role,
            message=message,
            response=response,
            response_time_ms=response_time_ms,
        )
        self.db.add(chat_message)
        await self.db.flush()
        return chat_message

    async def get_recent_by_session(
        self,
        session_id: int,
        limit: int,
    ) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def get_all_by_session_uuid(
        self,
        session_uuid: uuid.UUID,
    ) -> list[ChatMessage]:
        result = await self.db.execute(
            select(ChatMessage)
            .join(ChatSession)
            .where(
                ChatSession.uuid == session_uuid,
                ChatSession.deleted_at.is_(None),
                ChatMessage.deleted_at.is_(None),
            )
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def avg_response_time(self) -> float:
        result = await self.db.execute(
            select(func.avg(ChatMessage.response_time_ms)).where(
                ChatMessage.response_time_ms.isnot(None),
                ChatMessage.deleted_at.is_(None),
            )
        )
        value = result.scalar_one()
        return float(value) if value else 0.0

    async def count_by_session(self, session_id: int) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.deleted_at.is_(None),
            )
        )
        return result.scalar_one()


class DocumentVersionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pending(self, version: int) -> DocumentVersion:
        doc_version = DocumentVersion(
            version=version,
            status=DocumentVersionStatus.PENDING,
        )
        self.db.add(doc_version)
        await self.db.flush()
        return doc_version

    async def get_by_uuid(
        self,
        version_uuid: uuid.UUID,
    ) -> DocumentVersion | None:
        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.uuid == version_uuid,
                DocumentVersion.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> DocumentVersion | None:
        result = await self.db.execute(
            select(DocumentVersion).where(
                DocumentVersion.status == DocumentVersionStatus.ACTIVE,
                DocumentVersion.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[DocumentVersion]:
        result = await self.db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.deleted_at.is_(None))
            .order_by(DocumentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_next_version_number(self) -> int:
        result = await self.db.execute(
            select(func.max(DocumentVersion.version)).where(
                DocumentVersion.deleted_at.is_(None)
            )
        )
        max_version = result.scalar_one()
        return (max_version or 0) + 1

    async def archive_active(self) -> DocumentVersion | None:
        active = await self.get_active()
        if active:
            active.status = DocumentVersionStatus.ARCHIVED
            await self.db.flush()
        return active

    async def activate(self, doc_version: DocumentVersion) -> DocumentVersion:
        doc_version.status = DocumentVersionStatus.ACTIVE
        await self.db.flush()
        return doc_version

    async def count_all(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(DocumentVersion).where(
                DocumentVersion.deleted_at.is_(None)
            )
        )
        return result.scalar_one()


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        document_version_id: int,
        file_name: str,
        file_type: str,
        s3_path: str,
    ) -> Document:
        document = Document(
            document_version_id=document_version_id,
            file_name=file_name,
            file_type=file_type,
            s3_path=s3_path,
        )
        self.db.add(document)
        await self.db.flush()
        return document

    async def get_by_version_id(
        self,
        document_version_id: int,
    ) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(
                Document.document_version_id == document_version_id,
                Document.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Document).where(
                Document.deleted_at.is_(None)
            )
        )
        return result.scalar_one()


class EmbeddingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(
        self,
        document_version_id: int,
        chunks: list[str],
        embeddings: list[list[float]],
    ) -> None:
        for index, (chunk_text, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            self.db.add(
                Embedding(
                    document_version_id=document_version_id,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    chunk_index=index,
                )
            )
        await self.db.flush()

    async def search_active(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[tuple[str, list[float], float]]:
        active_version_subq = (
            select(DocumentVersion.id)
            .where(
                DocumentVersion.status == DocumentVersionStatus.ACTIVE,
                DocumentVersion.deleted_at.is_(None),
            )
            .scalar_subquery()
        )

        distance = Embedding.embedding.cosine_distance(query_embedding)
        result = await self.db.execute(
            select(
                Embedding.chunk_text,
                Embedding.embedding,
                distance.label("distance"),
            )
            .where(
                Embedding.document_version_id == active_version_subq,
                Embedding.deleted_at.is_(None),
            )
            .order_by(distance)
            .limit(top_k)
        )
        rows = result.all()
        return [
            (row.chunk_text, list(row.embedding), float(1 - row.distance))
            for row in rows
        ]


class EmbeddingArchiveRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, document_version_id: int) -> EmbeddingArchive:
        archive = EmbeddingArchive(
            document_version_id=document_version_id,
        )
        self.db.add(archive)
        await self.db.flush()
        return archive


class AuditLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        action: str,
        metadata: dict | None = None,
    ) -> AuditLog:
        log = AuditLog(action=action, metadata_=metadata)
        self.db.add(log)
        await self.db.flush()
        return log


class EvaluationLogRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        session_id: int | None,
        question: str,
        retrieved_chunks: list[str],
        answer: str,
        latency_ms: int,
        token_usage: dict,
        retrieval_score: float,
        grounding_score: float,
        quality_score: float,
    ) -> EvaluationLog:
        log = EvaluationLog(
            session_id=session_id,
            question=question,
            retrieved_chunks=retrieved_chunks,
            answer=answer,
            latency_ms=latency_ms,
            token_usage=token_usage,
            retrieval_score=retrieval_score,
            grounding_score=grounding_score,
            quality_score=quality_score,
        )
        self.db.add(log)
        await self.db.flush()
        return log

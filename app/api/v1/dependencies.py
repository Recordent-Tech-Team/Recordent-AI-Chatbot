from functools import lru_cache

import aioboto3
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.aws_session import get_aioboto3_session
from app.db.repositories import (
    AuditLogRepository,
    ChatMessageRepository,
    ChatSessionRepository,
    DocumentRepository,
    DocumentVersionRepository,
    EmbeddingArchiveRepository,
    EmbeddingRepository,
    EvaluationResultRepository,
    EvaluationRunRepository,
    EvaluationLogRepository,
    GoldenDatasetCaseRepository,
    GoldenDatasetRepository,
)
from app.db.session import get_db
from app.services.admin.admin_service import AdminService
from app.services.bedrock.chat_service import BedrockChatService
from app.services.bedrock.embedding_service import BedrockEmbeddingService
from app.services.chat.chat_service import ChatService
from app.services.evaluation.evaluation_service import EvaluationService
from app.services.evaluation.framework_service import (
    EvaluationFrameworkService,
)
from app.services.ingestion.ingestion_service import IngestionService
from app.services.retrieval.retrieval_service import RetrievalService
from app.services.s3.archive_service import S3ArchiveService
from app.services.s3.upload_service import S3UploadService


@lru_cache
def get_bedrock_chat_service() -> BedrockChatService:
    return BedrockChatService(get_aws_session())


@lru_cache
def get_bedrock_embedding_service() -> BedrockEmbeddingService:
    return BedrockEmbeddingService(get_aws_session())


@lru_cache
def get_s3_upload_service() -> S3UploadService:
    return S3UploadService(get_aws_session())


@lru_cache
def get_s3_archive_service() -> S3ArchiveService:
    return S3ArchiveService(get_aws_session())


@lru_cache
def get_aws_session() -> aioboto3.Session:
    return get_aioboto3_session()


def get_chat_service(
    db: AsyncSession = Depends(get_db),
    chat_service: BedrockChatService = Depends(get_bedrock_chat_service),
    embedding_service: BedrockEmbeddingService = Depends(
        get_bedrock_embedding_service
    ),
) -> ChatService:
    session_repo = ChatSessionRepository(db)
    message_repo = ChatMessageRepository(db)
    embedding_repo = EmbeddingRepository(db)
    evaluation_repo = EvaluationLogRepository(db)
    retrieval_service = RetrievalService(embedding_repo, embedding_service)
    evaluation_service = EvaluationService(evaluation_repo, chat_service)
    return ChatService(
        session_repo,
        message_repo,
        retrieval_service,
        chat_service,
        evaluation_service,
    )


def get_ingestion_service(
    db: AsyncSession = Depends(get_db),
    upload_service: S3UploadService = Depends(get_s3_upload_service),
    archive_service: S3ArchiveService = Depends(get_s3_archive_service),
    embedding_service: BedrockEmbeddingService = Depends(
        get_bedrock_embedding_service
    ),
) -> IngestionService:
    return IngestionService(
        DocumentVersionRepository(db),
        DocumentRepository(db),
        EmbeddingRepository(db),
        EmbeddingArchiveRepository(db),
        AuditLogRepository(db),
        upload_service,
        archive_service,
        embedding_service,
    )


def get_admin_service(
    db: AsyncSession = Depends(get_db),
) -> AdminService:
    return AdminService(
        DocumentVersionRepository(db),
        DocumentRepository(db),
        ChatSessionRepository(db),
        ChatMessageRepository(db),
        AuditLogRepository(db),
    )


def get_evaluation_framework_service(
    db: AsyncSession = Depends(get_db),
    chat_service: BedrockChatService = Depends(get_bedrock_chat_service),
    embedding_service: BedrockEmbeddingService = Depends(
        get_bedrock_embedding_service
    ),
) -> EvaluationFrameworkService:
    retrieval_service = RetrievalService(
        EmbeddingRepository(db),
        embedding_service,
    )
    return EvaluationFrameworkService(
        db=db,
        dataset_repo=GoldenDatasetRepository(db),
        case_repo=GoldenDatasetCaseRepository(db),
        run_repo=EvaluationRunRepository(db),
        result_repo=EvaluationResultRepository(db),
        retrieval_service=retrieval_service,
        chat_service=chat_service,
    )

import asyncio
import time

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.logger import get_logger
from app.db.repositories import (
    AuditLogRepository,
    DocumentRepository,
    DocumentVersionRepository,
    EmbeddingArchiveRepository,
    EmbeddingRepository,
)
from app.services.bedrock.embedding_service import BedrockEmbeddingService
from app.services.ingestion.chunking_service import chunk_text
from app.services.ingestion.text_extractor import extract_text
from app.services.s3.archive_service import S3ArchiveService
from app.services.s3.upload_service import S3UploadService

logger = get_logger("ingestion_service.py")

CONTENT_TYPES = {
    "pdf": "application/pdf",
    "docx": (
        "application/vnd.openxmlformats-officedocument"
        ".wordprocessingml.document"
    ),
    "txt": "text/plain",
}


class IngestionService:
    def __init__(
        self,
        version_repo: DocumentVersionRepository,
        document_repo: DocumentRepository,
        embedding_repo: EmbeddingRepository,
        archive_repo: EmbeddingArchiveRepository,
        audit_repo: AuditLogRepository,
        upload_service: S3UploadService,
        archive_service: S3ArchiveService,
        embedding_service: BedrockEmbeddingService,
    ):
        self.version_repo = version_repo
        self.document_repo = document_repo
        self.embedding_repo = embedding_repo
        self.archive_repo = archive_repo
        self.audit_repo = audit_repo
        self.upload_service = upload_service
        self.archive_service = archive_service
        self.embedding_service = embedding_service

    async def ingest_document(
        self,
        file_bytes: bytes,
        file_name: str,
        file_type: str,
        archive_current: bool = True,
    ):
        file_type = file_type.lower().lstrip(".")
        if file_type not in CONTENT_TYPES:
            raise ValidationError(
                f"Unsupported file type: {file_type}. "
                "Supported: pdf, docx, txt"
            )

        active_version = None
        if archive_current:
            active_version = await self.version_repo.archive_active()
            if active_version:
                docs = await self.document_repo.get_by_version_id(
                    active_version.id
                )
                source_keys = [doc.s3_path for doc in docs]
                if source_keys:
                    await self.archive_service.archive_objects(
                        source_keys,
                        str(active_version.uuid),
                    )
                await self.archive_repo.create(active_version.id)

        version_number = await self.version_repo.get_next_version_number()
        doc_version = await self.version_repo.create_pending(version_number)

        s3_key = self.upload_service.build_document_key(
            str(doc_version.uuid),
            file_name,
        )
        await self.upload_service.upload_file(
            file_bytes,
            s3_key,
            CONTENT_TYPES[file_type],
        )

        await self.document_repo.create(
            document_version_id=doc_version.id,
            file_name=file_name,
            file_type=file_type,
            s3_path=s3_key,
        )

        text = await extract_text(file_bytes, file_type)
        if not text:
            raise ValidationError("No text could be extracted from document")

        chunks = await asyncio.to_thread(
            chunk_text,
            text,
            settings.RAG_CHUNK_SIZE,
            settings.RAG_CHUNK_OVERLAP,
        )
        if not chunks:
            raise ValidationError("Chunk generation failed")

        logger.info(
            "Chunking completed for document "
            f"file_name={file_name}, "
            f"version_uuid={doc_version.uuid}, "
            f"total_chunks={len(chunks)}"
        )

        embedding_started = time.perf_counter()
        embedding_result = await self.embedding_service.embed_texts_with_metadata(
            chunks
        )
        embedding_duration_ms = int(
            (time.perf_counter() - embedding_started) * 1000
        )

        logger.info(
            "Embedding generation completed "
            f"file_name={file_name}, "
            f"version_uuid={doc_version.uuid}, "
            f"dimension={embedding_result.dimension}, "
            f"duration_ms={embedding_duration_ms}, "
            f"chunks={len(chunks)}"
        )

        await self.embedding_repo.bulk_create(
            doc_version.id,
            chunks,
            embedding_result.embeddings,
        )

        await self.version_repo.activate(doc_version)
        await self.audit_repo.create(
            action="embeddings_update",
            metadata={
                "version_uuid": str(doc_version.uuid),
                "version": doc_version.version,
                "file_name": file_name,
                "chunks": len(chunks),
                "embedding_model_id": embedding_result.model_id,
                "embedding_dimension": embedding_result.dimension,
                "embedding_duration_ms": embedding_duration_ms,
            },
        )

        logger.info(
            f"Ingested document version {doc_version.version} "
            f"with {len(chunks)} chunks"
        )
        return doc_version

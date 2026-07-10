import enum
import uuid as uuid_lib
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base

TABLES = {table_name: table_name for table_name in settings.DB_TABLES}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class DocumentVersionStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    PENDING = "pending"


class EvaluationRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class TimestampSoftDeleteMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class ChatSession(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["chat_sessions"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_lib.uuid4,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            schema=settings.DB_SCHEMA,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=SessionStatus.ACTIVE,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessage(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["chat_messages"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey(f"{TABLES['chat_sessions']}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class DocumentVersion(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["document_versions"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_lib.uuid4,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentVersionStatus] = mapped_column(
        Enum(
            DocumentVersionStatus,
            name="document_version_status",
            schema=settings.DB_SCHEMA,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=DocumentVersionStatus.PENDING,
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )
    archives: Mapped[list["EmbeddingArchive"]] = relationship(
        back_populates="document_version",
        cascade="all, delete-orphan",
    )


class Document(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["documents"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey(f"{TABLES['document_versions']}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    s3_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    document_version: Mapped["DocumentVersion"] = relationship(
        back_populates="documents",
    )


class Embedding(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["embeddings"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey(f"{TABLES['document_versions']}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(
        Vector(settings.BEDROCK_EMBEDDING_DIMENSION),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    document_version: Mapped["DocumentVersion"] = relationship(
        back_populates="embeddings",
    )


class EmbeddingArchive(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["embedding_archives"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_version_id: Mapped[int] = mapped_column(
        ForeignKey(f"{TABLES['document_versions']}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    document_version: Mapped["DocumentVersion"] = relationship(
        back_populates="archives",
    )


class AuditLog(Base):
    __tablename__ = TABLES["audit_logs"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class EvaluationLog(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["evaluation_logs"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{TABLES['chat_sessions']}.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grounding_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class GoldenDataset(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["golden_datasets"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_lib.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class GoldenDatasetCase(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["golden_dataset_cases"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_lib.uuid4,
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey(f"{TABLES['golden_datasets']}.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    expected_sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EvaluationRun(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["evaluation_runs"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid_lib.uuid4,
    )
    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{TABLES['golden_datasets']}.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[EvaluationRunStatus] = mapped_column(
        Enum(
            EvaluationRunStatus,
            name="evaluation_run_status",
            schema=settings.DB_SCHEMA,
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=EvaluationRunStatus.QUEUED,
    )
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_cases: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    failed_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvaluationResult(TimestampSoftDeleteMixin, Base):
    __tablename__ = TABLES["evaluation_results"]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(
        ForeignKey(f"{TABLES['evaluation_runs']}.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_case_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            f"{TABLES['golden_dataset_cases']}.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_context: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    recall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    correctness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevancy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    faithfulness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_supported: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

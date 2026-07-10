import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.db.models import DocumentVersionStatus
from app.db.repositories import (
    AuditLogRepository,
    ChatMessageRepository,
    ChatSessionRepository,
    DocumentRepository,
    DocumentVersionRepository,
)

logger = get_logger("admin_service.py")


class AdminService:
    def __init__(
        self,
        version_repo: DocumentVersionRepository,
        document_repo: DocumentRepository,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
        audit_repo: AuditLogRepository,
    ):
        self.version_repo = version_repo
        self.document_repo = document_repo
        self.session_repo = session_repo
        self.message_repo = message_repo
        self.audit_repo = audit_repo

    async def list_versions(self) -> list[dict]:
        versions = await self.version_repo.list_all()
        result = []
        for version in versions:
            docs = await self.document_repo.get_by_version_id(version.id)
            result.append({
                "version_id": str(version.uuid),
                "version": version.version,
                "status": version.status.value,
                "created_at": version.created_at.isoformat(),
                "documents": [
                    {
                        "file_name": doc.file_name,
                        "file_type": doc.file_type,
                        "s3_path": doc.s3_path,
                    }
                    for doc in docs
                ],
            })
        return result

    async def rollback(self, version_uuid: uuid.UUID) -> dict:
        target = await self.version_repo.get_by_uuid(version_uuid)
        if not target:
            raise NotFoundError("Version not found")

        if target.status == DocumentVersionStatus.ACTIVE:
            raise ValidationError("Version is already active")

        await self.version_repo.archive_active()
        await self.version_repo.activate(target)
        await self.audit_repo.create(
            action="embeddings_rollback",
            metadata={"version_uuid": str(version_uuid)},
        )
        return {
            "version_id": str(target.uuid),
            "version": target.version,
            "status": target.status.value,
        }

    async def list_sessions(
        self,
        page: int,
        size: int,
    ) -> dict:
        sessions, total = await self.session_repo.list_paginated(
            page,
            size,
        )
        items = []
        for session in sessions:
            message_count = await self.message_repo.count_by_session(
                session.id
            )
            items.append({
                "session_id": str(session.uuid),
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "closed_at": (
                    session.closed_at.isoformat()
                    if session.closed_at
                    else None
                ),
                "message_count": message_count,
            })
        return {
            "items": items,
            "page": page,
            "size": size,
            "total": total,
            "total_pages": (total + size - 1) // size,
        }

    async def get_session_history(
        self,
        session_uuid: uuid.UUID,
    ) -> dict:
        session = await self.session_repo.get_by_uuid(session_uuid)
        if not session:
            raise NotFoundError("Session not found")

        messages = await self.message_repo.get_all_by_session_uuid(
            session_uuid
        )
        return {
            "session_id": str(session_uuid),
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "closed_at": (
                session.closed_at.isoformat()
                if session.closed_at
                else None
            ),
            "messages": [
                {
                    "role": msg.role,
                    "message": msg.message,
                    "response": msg.response,
                    "response_time_ms": msg.response_time_ms,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ],
        }

    async def get_analytics(self) -> dict:
        total_sessions = await self.session_repo.count_all()
        total_messages = await self.message_repo.count_all()
        avg_response_time = await self.message_repo.avg_response_time()
        document_count = await self.document_repo.count_all()
        version_count = await self.version_repo.count_all()

        avg_session_length = 0.0
        if total_sessions > 0:
            avg_session_length = total_messages / total_sessions

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "average_session_length": round(avg_session_length, 2),
            "average_response_time_ms": round(avg_response_time, 2),
            "document_count": document_count,
            "version_count": version_count,
        }

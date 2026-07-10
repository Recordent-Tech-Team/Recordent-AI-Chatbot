import uuid

from pydantic import BaseModel, Field


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID


class ChatMessageRequest(BaseModel):
    session_id: uuid.UUID
    message: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    session_id: uuid.UUID
    response: str
    response_time_ms: int


class CloseSessionRequest(BaseModel):
    session_id: uuid.UUID


class CloseSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str


class RollbackRequest(BaseModel):
    version_id: uuid.UUID

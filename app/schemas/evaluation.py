import uuid
from typing import Any

from pydantic import BaseModel, Field


class GoldenDatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class GoldenDatasetCaseRequest(BaseModel):
    question: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    expected_sources: list[str] = Field(default_factory=list)


class GoldenDatasetBulkCasesRequest(BaseModel):
    cases: list[GoldenDatasetCaseRequest] = Field(..., min_length=1)


class SingleEvaluationRequest(BaseModel):
    question: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    expected_sources: list[str] = Field(default_factory=list)


class RunBenchmarkRequest(BaseModel):
    dataset_id: uuid.UUID


class EvaluationHistoryQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    run_id: uuid.UUID | None = None
    dataset_id: uuid.UUID | None = None


class EvaluationResultDTO(BaseModel):
    id: int
    run_id: uuid.UUID | None
    question: str
    expected_answer: str
    generated_answer: str
    retrieved_context: list[dict[str, Any]] | None
    recall_score: float | None
    precision_score: float | None
    correctness_score: float | None
    relevancy_score: float | None
    completeness_score: float | None
    faithfulness_score: float | None
    hallucination_score: float | None
    citation_supported: bool | None
    overall_score: float | None
    created_at: str


class EvaluationRunStatusDTO(BaseModel):
    run_id: uuid.UUID
    dataset_id: uuid.UUID | None
    status: str
    total_cases: int
    completed_cases: int
    failed_cases: int
    error_message: str | None
    created_at: str
    updated_at: str

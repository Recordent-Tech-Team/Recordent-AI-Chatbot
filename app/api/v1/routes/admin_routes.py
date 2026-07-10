import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.api.v1.dependencies import (
    get_admin_service,
    get_evaluation_framework_service,
    get_ingestion_service,
)
from app.core.logger import get_logger
from app.core.responses import success
from app.core.security import verify_admin_api_secret
from app.schemas.chat import RollbackRequest
from app.schemas.evaluation import (
    GoldenDatasetBulkCasesRequest,
    GoldenDatasetCreateRequest,
    RunBenchmarkRequest,
    SingleEvaluationRequest,
)
from app.services.admin.admin_service import AdminService
from app.services.evaluation.framework_service import (
    EvaluationFrameworkService,
)
from app.services.ingestion.ingestion_service import IngestionService

logger = get_logger("admin_routes.py")

router = APIRouter(
    prefix="/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_api_secret)],
)


@router.post("/embeddings/update")
async def update_embeddings(
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    file_bytes = await file.read()
    file_name = file.filename or "document"
    file_type = file_name.rsplit(".", 1)[-1].lower()
    doc_version = await ingestion_service.ingest_document(
        file_bytes=file_bytes,
        file_name=file_name,
        file_type=file_type,
        archive_current=True,
    )
    return success(
        message="Success",
        data={
            "version_id": str(doc_version.uuid),
            "version": doc_version.version,
            "status": doc_version.status.value,
        },
        http_status=200,
    )


@router.get("/embeddings/versions")
async def list_versions(
    admin_service: AdminService = Depends(get_admin_service),
):
    return success(
        message="Success",
        data={"versions": await admin_service.list_versions()},
        http_status=200,
    )


@router.post("/embeddings/rollback")
async def rollback_version(
    request: RollbackRequest,
    admin_service: AdminService = Depends(get_admin_service),
):
    result = await admin_service.rollback(request.version_id)
    return success(
        message="Success",
        data=result,
        http_status=200,
    )


@router.get("/chat/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=0, le=100),
    admin_service: AdminService = Depends(get_admin_service),
):
    effective_size = size or 20
    return success(
        message="Success",
        data=await admin_service.list_sessions(page, effective_size),
        http_status=200,
    )


@router.get("/chat/history")
async def get_chat_history(
    session_id: uuid.UUID = Query(...),
    admin_service: AdminService = Depends(get_admin_service),
):
    return success(
        message="Success",
        data=await admin_service.get_session_history(session_id),
        http_status=200,
    )


@router.get("/analytics")
async def get_analytics(
    admin_service: AdminService = Depends(get_admin_service),
):
    return success(
        message="Success",
        data=await admin_service.get_analytics(),
        http_status=200,
    )


@router.post("/evaluation/golden-datasets")
async def create_golden_dataset(
    request: GoldenDatasetCreateRequest,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.create_dataset(
            name=request.name,
            description=request.description,
        ),
        http_status=201,
    )


@router.get("/evaluation/golden-datasets")
async def list_golden_datasets(
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.list_datasets(),
        http_status=200,
    )


@router.post("/evaluation/golden-datasets/{dataset_id}/cases:bulk")
async def bulk_add_golden_cases(
    dataset_id: uuid.UUID,
    request: GoldenDatasetBulkCasesRequest,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.add_cases_bulk(
            dataset_uuid=dataset_id,
            cases=[case.model_dump() for case in request.cases],
        ),
        http_status=201,
    )


@router.get("/evaluation/golden-datasets/{dataset_id}/cases")
async def list_golden_cases(
    dataset_id: uuid.UUID,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.list_cases(dataset_uuid=dataset_id),
        http_status=200,
    )


@router.post("/evaluation/run-single")
async def run_single_evaluation(
    request: SingleEvaluationRequest,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.run_single_evaluation(
            question=request.question,
            expected_answer=request.expected_answer,
            expected_sources=request.expected_sources,
        ),
        http_status=200,
    )


@router.post("/evaluation/run-benchmark")
async def run_full_benchmark(
    request: RunBenchmarkRequest,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.run_full_benchmark(
            dataset_uuid=request.dataset_id,
        ),
        http_status=202,
    )


@router.get("/evaluation/runs/{run_id}")
async def get_benchmark_run_status(
    run_id: uuid.UUID,
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.get_run_status(run_id),
        http_status=200,
    )


@router.get("/evaluation/history")
async def get_evaluation_history(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    run_id: uuid.UUID | None = Query(None),
    dataset_id: uuid.UUID | None = Query(None),
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.get_history(
            page=page,
            size=size,
            run_uuid=run_id,
            dataset_uuid=dataset_id,
        ),
        http_status=200,
    )


@router.get("/evaluation/metrics")
async def get_evaluation_metrics(
    run_id: uuid.UUID | None = Query(None),
    dataset_id: uuid.UUID | None = Query(None),
    evaluation_service: EvaluationFrameworkService = Depends(
        get_evaluation_framework_service
    ),
):
    return success(
        message="Success",
        data=await evaluation_service.get_aggregated_metrics(
            run_uuid=run_id,
            dataset_uuid=dataset_id,
        ),
        http_status=200,
    )

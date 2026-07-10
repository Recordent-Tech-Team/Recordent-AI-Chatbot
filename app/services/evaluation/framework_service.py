import asyncio
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.aws_session import get_aioboto3_session
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.db.models import GoldenDataset
from app.db.repositories import (
    EmbeddingRepository,
    EvaluationResultRepository,
    EvaluationRunRepository,
    GoldenDatasetCaseRepository,
    GoldenDatasetRepository,
)
from app.db.session import AsyncSessionLocal
from app.services.bedrock.chat_service import BedrockChatService
from app.services.bedrock.embedding_service import BedrockEmbeddingService
from app.services.retrieval.retrieval_service import RetrievalService

logger = get_logger("framework_service.py")

try:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    DEEPEVAL_AVAILABLE = True
except Exception:
    DEEPEVAL_AVAILABLE = False


class EvaluationFrameworkService:
    _background_tasks: set[asyncio.Task] = set()

    def __init__(
        self,
        db: AsyncSession,
        dataset_repo: GoldenDatasetRepository,
        case_repo: GoldenDatasetCaseRepository,
        run_repo: EvaluationRunRepository,
        result_repo: EvaluationResultRepository,
        retrieval_service: RetrievalService,
        chat_service: BedrockChatService,
    ):
        self.db = db
        self.dataset_repo = dataset_repo
        self.case_repo = case_repo
        self.run_repo = run_repo
        self.result_repo = result_repo
        self.retrieval_service = retrieval_service
        self.chat_service = chat_service

    async def create_dataset(self, name: str, description: str | None) -> dict:
        dataset = await self.dataset_repo.create(name=name, description=description)
        return {
            "dataset_id": str(dataset.uuid),
            "name": dataset.name,
            "description": dataset.description,
            "created_at": dataset.created_at.isoformat(),
        }

    async def list_datasets(self) -> dict:
        datasets = await self.dataset_repo.list_all()
        items = []
        for dataset in datasets:
            case_count = await self.case_repo.count_by_dataset(dataset.id)
            items.append({
                "dataset_id": str(dataset.uuid),
                "name": dataset.name,
                "description": dataset.description,
                "case_count": case_count,
                "created_at": dataset.created_at.isoformat(),
            })
        return {"items": items}

    async def add_cases_bulk(
        self,
        dataset_uuid: uuid.UUID,
        cases: list[dict],
    ) -> dict:
        dataset = await self.dataset_repo.get_by_uuid(dataset_uuid)
        if not dataset:
            raise NotFoundError("Dataset not found")

        if len(cases) > 1000:
            raise ValidationError("Max 1000 cases are allowed per bulk request")

        created_count = await self.case_repo.bulk_create(
            dataset_id=dataset.id,
            cases=cases,
        )
        return {
            "dataset_id": str(dataset.uuid),
            "created_count": created_count,
        }

    async def list_cases(self, dataset_uuid: uuid.UUID) -> dict:
        dataset = await self.dataset_repo.get_by_uuid(dataset_uuid)
        if not dataset:
            raise NotFoundError("Dataset not found")

        cases = await self.case_repo.list_by_dataset(dataset.id)
        return {
            "dataset_id": str(dataset.uuid),
            "name": dataset.name,
            "items": [
                {
                    "case_id": str(case.uuid),
                    "question": case.question,
                    "expected_answer": case.expected_answer,
                    "expected_sources": case.expected_sources or [],
                }
                for case in cases
            ],
        }

    async def run_single_evaluation(
        self,
        question: str,
        expected_answer: str,
        expected_sources: list[str],
    ) -> dict:
        return await self._evaluate_case(
            question=question,
            expected_answer=expected_answer,
            expected_sources=expected_sources,
            run_id=None,
            dataset_case_id=None,
        )

    async def run_full_benchmark(self, dataset_uuid: uuid.UUID) -> dict:
        dataset = await self.dataset_repo.get_by_uuid(dataset_uuid)
        if not dataset:
            raise NotFoundError("Dataset not found")

        cases = await self.case_repo.list_by_dataset(dataset.id)
        if not cases:
            raise ValidationError("Dataset has no active cases")

        run = await self.run_repo.create(
            dataset_id=dataset.id,
            total_cases=len(cases),
        )

        task = asyncio.create_task(
            self._execute_benchmark_background(
                run_uuid=run.uuid,
                dataset_uuid=dataset.uuid,
            )
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

        return {
            "run_id": str(run.uuid),
            "dataset_id": str(dataset.uuid),
            "status": run.status.value,
            "total_cases": run.total_cases,
        }

    async def get_run_status(self, run_uuid: uuid.UUID) -> dict:
        run = await self.run_repo.get_by_uuid(run_uuid)
        if not run:
            raise NotFoundError("Run not found")

        dataset_uuid = None
        if run.dataset_id is not None:
            dataset = await self.db.get(GoldenDataset, run.dataset_id)
            if dataset is not None and getattr(dataset, "uuid", None):
                dataset_uuid = str(dataset.uuid)

        return {
            "run_id": str(run.uuid),
            "dataset_id": dataset_uuid,
            "status": run.status.value,
            "total_cases": run.total_cases,
            "completed_cases": run.completed_cases,
            "failed_cases": run.failed_cases,
            "error_message": run.error_message,
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
        }

    async def get_history(
        self,
        page: int,
        size: int,
        run_uuid: uuid.UUID | None,
        dataset_uuid: uuid.UUID | None,
    ) -> dict:
        run_id = None
        dataset_id = None

        if run_uuid is not None:
            run = await self.run_repo.get_by_uuid(run_uuid)
            if not run:
                raise NotFoundError("Run not found")
            run_id = run.id

        if dataset_uuid is not None:
            dataset = await self.dataset_repo.get_by_uuid(dataset_uuid)
            if not dataset:
                raise NotFoundError("Dataset not found")
            dataset_id = dataset.id

        rows, total = await self.result_repo.list_history(
            page=page,
            size=size,
            run_id=run_id,
            dataset_id=dataset_id,
        )

        run_id_values = [row.run_id for row in rows if row.run_id is not None]
        runs = await self.run_repo.get_by_ids(run_id_values)
        run_uuid_map = {run.id: str(run.uuid) for run in runs}

        items = []
        for row in rows:
            run_uuid_value = run_uuid_map.get(row.run_id)
            items.append({
                "id": row.id,
                "run_id": run_uuid_value,
                "question": row.question,
                "expected_answer": row.expected_answer,
                "generated_answer": row.generated_answer,
                "retrieved_context": row.retrieved_context,
                "recall_score": row.recall_score,
                "precision_score": row.precision_score,
                "correctness_score": row.correctness_score,
                "relevancy_score": row.relevancy_score,
                "completeness_score": row.completeness_score,
                "faithfulness_score": row.faithfulness_score,
                "hallucination_score": row.hallucination_score,
                "citation_supported": row.citation_supported,
                "overall_score": row.overall_score,
                "created_at": row.created_at.isoformat(),
            })

        return {
            "items": items,
            "page": page,
            "size": size,
            "total": total,
            "total_pages": (total + size - 1) // size,
        }

    async def get_aggregated_metrics(
        self,
        run_uuid: uuid.UUID | None,
        dataset_uuid: uuid.UUID | None,
    ) -> dict:
        run_id = None
        dataset_id = None

        if run_uuid is not None:
            run = await self.run_repo.get_by_uuid(run_uuid)
            if not run:
                raise NotFoundError("Run not found")
            run_id = run.id

        if dataset_uuid is not None:
            dataset = await self.dataset_repo.get_by_uuid(dataset_uuid)
            if not dataset:
                raise NotFoundError("Dataset not found")
            dataset_id = dataset.id

        return await self.result_repo.get_aggregates(
            run_id=run_id,
            dataset_id=dataset_id,
        )

    async def _execute_benchmark_background(
        self,
        run_uuid: uuid.UUID,
        dataset_uuid: uuid.UUID,
    ) -> None:
        completed = 0
        failed = 0

        async with AsyncSessionLocal() as db:
            dataset_repo = GoldenDatasetRepository(db)
            case_repo = GoldenDatasetCaseRepository(db)
            run_repo = EvaluationRunRepository(db)
            result_repo = EvaluationResultRepository(db)

            aws_session = get_aioboto3_session()
            chat_service = BedrockChatService(aws_session)
            embedding_service = BedrockEmbeddingService(aws_session)
            retrieval_service = RetrievalService(
                embedding_repo=EmbeddingRepository(db),
                embedding_service=embedding_service,
            )

            service = EvaluationFrameworkService(
                db=db,
                dataset_repo=dataset_repo,
                case_repo=case_repo,
                run_repo=run_repo,
                result_repo=result_repo,
                retrieval_service=retrieval_service,
                chat_service=chat_service,
            )

            run = await run_repo.get_by_uuid(run_uuid)
            dataset = await dataset_repo.get_by_uuid(dataset_uuid)
            if not run or not dataset:
                return

            await run_repo.mark_running(run)
            await db.commit()

            cases = await case_repo.list_by_dataset(dataset.id)

            for case in cases:
                try:
                    await service._evaluate_case(
                        question=case.question,
                        expected_answer=case.expected_answer,
                        expected_sources=case.expected_sources or [],
                        run_id=run.id,
                        dataset_case_id=case.id,
                    )
                    completed += 1
                except Exception as error:
                    failed += 1
                    logger.error(f"Benchmark case failed: {error}")
                finally:
                    await run_repo.update_progress(
                        run=run,
                        completed_cases=completed,
                        failed_cases=failed,
                    )
                    await db.commit()

            try:
                await run_repo.mark_completed(
                    run=run,
                    completed_cases=completed,
                    failed_cases=failed,
                )
                await db.commit()
            except Exception as error:
                await run_repo.mark_failed(
                    run=run,
                    error_message=str(error),
                    completed_cases=completed,
                    failed_cases=failed,
                )
                await db.commit()

    async def _evaluate_case(
        self,
        question: str,
        expected_answer: str,
        expected_sources: list[str],
        run_id: int | None,
        dataset_case_id: int | None,
    ) -> dict:
        retrieved = await self.retrieval_service.retrieve(question)
        retrieved_context = [
            {
                "chunk": chunk,
                "score": float(score),
            }
            for chunk, score in retrieved
        ]

        context_text = "\n\n".join(item["chunk"] for item in retrieved_context)
        llm_answer = await self.chat_service.generate(
            context=context_text,
            question=question,
            history=[],
        )
        generated_answer = llm_answer.answer

        recall_score, precision_score = self._context_recall_precision(
            expected_sources=expected_sources,
            retrieved_context=[item["chunk"] for item in retrieved_context],
        )

        correctness_score = await self._score_correctness(
            question=question,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
        )
        relevancy_score = await self._score_relevancy(
            question=question,
            generated_answer=generated_answer,
        )
        completeness_score = await self._score_completeness(
            expected_answer=expected_answer,
            generated_answer=generated_answer,
        )
        faithfulness_score = await self._score_faithfulness(
            context=context_text,
            generated_answer=generated_answer,
        )
        hallucination_score = await self._score_hallucination(
            context=context_text,
            generated_answer=generated_answer,
        )

        citation_supported = self._validate_citations(
            generated_answer=generated_answer,
            retrieved_context=[item["chunk"] for item in retrieved_context],
        )

        overall_score = self._compute_overall_score(
            recall_score=recall_score,
            precision_score=precision_score,
            correctness_score=correctness_score,
            faithfulness_score=faithfulness_score,
            completeness_score=completeness_score,
        )

        saved = await self.result_repo.create(
            run_id=run_id,
            dataset_case_id=dataset_case_id,
            question=question,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
            retrieved_context=retrieved_context,
            recall_score=recall_score,
            precision_score=precision_score,
            correctness_score=correctness_score,
            relevancy_score=relevancy_score,
            completeness_score=completeness_score,
            faithfulness_score=faithfulness_score,
            hallucination_score=hallucination_score,
            citation_supported=citation_supported,
            overall_score=overall_score,
        )

        return {
            "evaluation_result_id": saved.id,
            "question": question,
            "expected_answer": expected_answer,
            "generated_answer": generated_answer,
            "retrieved_context": retrieved_context,
            "recall_score": recall_score,
            "precision_score": precision_score,
            "correctness_score": correctness_score,
            "relevancy_score": relevancy_score,
            "completeness_score": completeness_score,
            "faithfulness_score": faithfulness_score,
            "hallucination_score": hallucination_score,
            "citation_supported": citation_supported,
            "overall_score": overall_score,
            "created_at": saved.created_at.isoformat(),
            "deepeval_enabled": DEEPEVAL_AVAILABLE,
        }

    async def _score_correctness(
        self,
        question: str,
        expected_answer: str,
        generated_answer: str,
    ) -> float:
        deepeval_score = self._try_deepeval_score(
            metric_name="Correctness",
            criteria=(
                "Compare actual output with expected output for factual correctness"
            ),
            question=question,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
        )
        if deepeval_score is not None:
            return deepeval_score

        prompt = f"""Rate from 0.0 to 1.0 how correct the generated answer is compared to expected answer.
Return only decimal.

QUESTION:
{question}

EXPECTED ANSWER:
{expected_answer}

GENERATED ANSWER:
{generated_answer}
"""
        return await self.chat_service.judge_score(prompt)

    async def _score_relevancy(
        self,
        question: str,
        generated_answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 how relevant the generated answer is to the user question.
Return only decimal.

QUESTION:
{question}

GENERATED ANSWER:
{generated_answer}
"""
        return await self.chat_service.judge_score(prompt)

    async def _score_completeness(
        self,
        expected_answer: str,
        generated_answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 how complete the generated answer is compared to expected answer.
Return only decimal.

EXPECTED ANSWER:
{expected_answer}

GENERATED ANSWER:
{generated_answer}
"""
        return await self.chat_service.judge_score(prompt)

    async def _score_faithfulness(
        self,
        context: str,
        generated_answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 how faithful the generated answer is to the provided context.
Return only decimal.

CONTEXT:
{context}

GENERATED ANSWER:
{generated_answer}
"""
        return await self.chat_service.judge_score(prompt)

    async def _score_hallucination(
        self,
        context: str,
        generated_answer: str,
    ) -> float:
        prompt = f"""Rate from 0.0 to 1.0 hallucination severity in generated answer based on context.
0.0 means no hallucination and 1.0 means severe hallucination.
Return only decimal.

CONTEXT:
{context}

GENERATED ANSWER:
{generated_answer}
"""
        return await self.chat_service.judge_score(prompt)

    def _context_recall_precision(
        self,
        expected_sources: list[str],
        retrieved_context: list[str],
    ) -> tuple[float, float]:
        if not expected_sources:
            return 0.0, 0.0

        matched_expected = 0
        for source in expected_sources:
            if any(self._has_overlap(source, chunk) for chunk in retrieved_context):
                matched_expected += 1

        matched_chunks = 0
        for chunk in retrieved_context:
            if any(self._has_overlap(chunk, source) for source in expected_sources):
                matched_chunks += 1

        recall = matched_expected / len(expected_sources) if expected_sources else 0.0
        precision = (
            matched_chunks / len(retrieved_context)
            if retrieved_context
            else 0.0
        )
        return round(recall, 4), round(precision, 4)

    def _validate_citations(
        self,
        generated_answer: str,
        retrieved_context: list[str],
    ) -> bool:
        answer_sentences = [
            sentence.strip()
            for sentence in re.split(r"[.!?]", generated_answer)
            if sentence.strip()
        ]
        if not answer_sentences:
            return False

        for sentence in answer_sentences[:5]:
            if any(self._has_overlap(sentence, chunk) for chunk in retrieved_context):
                return True
        return False

    def _compute_overall_score(
        self,
        recall_score: float,
        precision_score: float,
        correctness_score: float,
        faithfulness_score: float,
        completeness_score: float,
    ) -> float:
        weighted = (
            recall_score * settings.EVALUATION_WEIGHT_RECALL
            + precision_score * settings.EVALUATION_WEIGHT_PRECISION
            + correctness_score * settings.EVALUATION_WEIGHT_CORRECTNESS
            + faithfulness_score * settings.EVALUATION_WEIGHT_FAITHFULNESS
            + completeness_score * settings.EVALUATION_WEIGHT_COMPLETENESS
        )
        return round(weighted, 4)

    def _has_overlap(self, a: str, b: str) -> bool:
        a_tokens = self._tokenize(a)
        b_tokens = self._tokenize(b)
        if not a_tokens or not b_tokens:
            return False
        overlap = len(a_tokens & b_tokens)
        baseline = min(len(a_tokens), len(b_tokens))
        return (overlap / baseline) >= 0.3

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
            if len(token) > 2
        }

    def _try_deepeval_score(
        self,
        metric_name: str,
        criteria: str,
        question: str,
        expected_answer: str,
        generated_answer: str,
    ) -> float | None:
        if not DEEPEVAL_AVAILABLE:
            return None

        try:
            test_case = LLMTestCase(
                input=question,
                expected_output=expected_answer,
                actual_output=generated_answer,
            )
            metric = GEval(
                name=metric_name,
                criteria=criteria,
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.EXPECTED_OUTPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                ],
            )
            metric.measure(test_case)
            if metric.score is None:
                return None
            return max(0.0, min(1.0, float(metric.score)))
        except Exception as error:
            logger.error(f"DeepEval scoring failed for {metric_name}: {error}")
            return None

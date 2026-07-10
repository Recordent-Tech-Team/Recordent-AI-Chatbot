import asyncio
import json
import random
from dataclasses import dataclass

import aioboto3

from app.core.config import settings
from app.core.error_codes import ErrorCodes
from app.core.exceptions import AppException
from app.core.logger import get_logger
from app.utils.aws_errors import to_aws_auth_app_exception

logger = get_logger("embedding_service.py")


@dataclass
class EmbeddingBatchResult:
    embeddings: list[list[float]]
    model_id: str
    dimension: int


class BedrockEmbeddingService:
    def __init__(self, aws_session: aioboto3.Session):
        self._session = aws_session
        self._model_id = settings.BEDROCK_EMBEDDING_MODEL_ID
        self._dimension = settings.BEDROCK_EMBEDDING_DIMENSION
        self._max_concurrency = max(
            1,
            settings.BEDROCK_EMBEDDING_MAX_CONCURRENCY,
        )
        self._max_retries = settings.BEDROCK_EMBEDDING_MAX_RETRIES
        self._base_backoff_seconds = (
            settings.BEDROCK_EMBEDDING_BASE_BACKOFF_SECONDS
        )
        self._request_interval_seconds = (
            settings.BEDROCK_EMBEDDING_REQUEST_INTERVAL_SECONDS
        )
        self._request_count = 0
        self._request_count_lock = asyncio.Lock()

    async def _next_request_count(self) -> int:
        async with self._request_count_lock:
            self._request_count += 1
            return self._request_count

    async def _invoke_model_with_retry(
        self,
        client,
        body: str,
        request_number: int,
        total_requests: int,
        chunk_length: int,
    ) -> tuple[dict, str, int]:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.invoke_model(
                    modelId=self._model_id,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
                payload = json.loads(await response["body"].read())
                aws_request_id = response.get(
                    "ResponseMetadata",
                    {},
                ).get("RequestId", "unknown")
                retries_used = attempt - 1
                return payload, aws_request_id, retries_used
            except Exception as error:
                last_error = error
                error_message = str(error)
                mapped_exception = to_aws_auth_app_exception(
                    error,
                    service_name="Bedrock Runtime",
                    operation="InvokeModel",
                )
                if mapped_exception:
                    raise mapped_exception from error
                is_throttled = (
                    "ThrottlingException" in error_message
                    or "Too many requests" in error_message
                )
                is_access_denied = (
                    "AccessDeniedException" in error_message
                    or "INVALID_PAYMENT_INSTRUMENT" in error_message
                    or "not authorized" in error_message.lower()
                )

                if is_access_denied:
                    raise AppException(
                        message=(
                            "Bedrock model access denied for "
                            f"model_id={self._model_id}. "
                            "Ensure model access/subscription and billing "
                            "are enabled in this AWS account."
                        ),
                        status_code=403,
                        err_code=ErrorCodes.FORBIDDEN,
                    )

                if not is_throttled:
                    raise AppException(
                        message=(
                            "Bedrock embedding request failed for "
                            f"model_id={self._model_id}. "
                            f"Details: {error_message}"
                        ),
                        status_code=500,
                        err_code=ErrorCodes.INTERNAL_SERVER_ERROR,
                    ) from error

                if attempt == self._max_retries:
                    break

                jitter = random.uniform(0.0, 0.25)
                delay = min(
                    self._base_backoff_seconds * (2 ** (attempt - 1))
                    + jitter,
                    12.0,
                )
                logger.info(
                    "Bedrock throttled for request "
                    f"{request_number}/{total_requests} "
                    f"chunk_length={chunk_length} "
                    f"(attempt {attempt}/{self._max_retries}). "
                    f"Retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)

        raise AppException(
            message=(
                "Bedrock embedding is throttled for "
                f"model_id={self._model_id}. "
                "Please retry after some time or request a Bedrock quota "
                "increase for this model in the selected region."
            ),
            status_code=429,
            err_code=ErrorCodes.TOO_MANY_REQUESTS,
        ) from last_error

    async def embed_text(self, text: str) -> list[float]:
        result = await self.embed_texts_with_metadata([text], for_query=True)
        return result.embeddings[0]

    @staticmethod
    def _build_request_body(
        text: str,
        dimension: int,
        for_query: bool,
    ) -> str:
        _ = for_query
        return json.dumps({
            "inputText": text,
            "dimensions": dimension,
            "normalize": True,
        })

    @staticmethod
    def _extract_embedding_and_tokens(
        payload: dict,
    ) -> tuple[list[float], int | None]:
        embedding = payload.get("embedding", [])
        token_count = payload.get("inputTextTokenCount")
        if isinstance(embedding, list):
            return embedding, token_count
        return [], token_count

    async def _embed_single_text(
        self,
        client,
        semaphore: asyncio.Semaphore,
        index: int,
        text: str,
        for_query: bool,
        total_requests: int,
        result_buffer: list[list[float] | None],
    ) -> None:
        async with semaphore:
            request_number = await self._next_request_count()
            chunk_length = len(text)
            body = self._build_request_body(
                text=text,
                dimension=self._dimension,
                for_query=for_query,
            )
            payload, aws_request_id, retries_used = await self._invoke_model_with_retry(
                client,
                body,
                request_number,
                total_requests,
                chunk_length,
            )
            embedding, token_count = self._extract_embedding_and_tokens(payload)
            if len(embedding) != self._dimension:
                raise ValueError(
                    "Unexpected embedding dimension "
                    f"{len(embedding)} for model_id={self._model_id}. "
                    f"Expected {self._dimension}."
                )

            result_buffer[index] = embedding
            await asyncio.sleep(self._request_interval_seconds)

    async def embed_texts_with_metadata(
        self,
        texts: list[str],
        for_query: bool = False,
    ) -> EmbeddingBatchResult:
        if not texts:
            return EmbeddingBatchResult(
                embeddings=[],
                model_id=self._model_id,
                dimension=self._dimension,
            )

        self._request_count = 0
        async with self._session.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
        ) as client:
            semaphore = asyncio.Semaphore(self._max_concurrency)
            result_buffer: list[list[float] | None] = [None] * len(texts)
            tasks = [
                self._embed_single_text(
                    client,
                    semaphore,
                    index,
                    text,
                    for_query,
                    len(texts),
                    result_buffer,
                )
                for index, text in enumerate(texts)
            ]
            await asyncio.gather(*tasks)

        embeddings = [embedding for embedding in result_buffer if embedding is not None]
        return EmbeddingBatchResult(
            embeddings=embeddings,
            model_id=self._model_id,
            dimension=self._dimension,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        result = await self.embed_texts_with_metadata(texts)
        return result.embeddings

    async def validate_model(self) -> None:
        sample = await self.embed_text("health check")
        if len(sample) != self._dimension:
            raise AppException(
                message=(
                    "Embedding model validation failed: "
                    f"expected dimension={self._dimension}, got={len(sample)}"
                ),
                status_code=500,
                err_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            )

from dataclasses import dataclass

import aioboto3

from app.core.config import settings
from app.core.error_codes import ErrorCodes
from app.core.exceptions import AppException
from app.core.logger import get_logger

logger = get_logger("chat_service.py")


@dataclass
class ChatResult:
    answer: str
    input_tokens: int
    output_tokens: int


class BedrockChatService:
    def __init__(self, aws_session: aioboto3.Session):
        self._session = aws_session
        self._model_id = settings.BEDROCK_CHAT_MODEL_ID
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        try:
            with open(
                settings.SYSTEM_PROMPT_PATH,
                "r",
                encoding="utf-8",
            ) as file:
                return file.read()
        except Exception as error:
            logger.error(f"System prompt loading failed: {error}")
            return ""

    async def generate(
        self,
        context: str,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        user_content = self._build_user_prompt(context, question)
        messages = []

        if history:
            for item in history:
                messages.append({
                    "role": item["role"],
                    "content": [{"text": item["content"]}],
                })

        messages.append({
            "role": "user",
            "content": [{"text": user_content}],
        })

        request_body = {
            "messages": messages,
            "system": [{"text": self._system_prompt}],
            "inferenceConfig": {
                "temperature": 0.2,
                "maxTokens": 800,
            },
        }

        async with self._session.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
        ) as client:
            response = await client.converse(
                modelId=self._model_id,
                messages=request_body["messages"],
                system=request_body["system"],
                inferenceConfig=request_body["inferenceConfig"],
            )

        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        answer = ""
        for block in content_blocks:
            if "text" in block:
                answer += block["text"]

        usage = response.get("usage", {})
        return ChatResult(
            answer=answer.strip(),
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
        )

    async def judge_score(
        self,
        prompt: str,
    ) -> float:
        async with self._session.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
        ) as client:
            response = await client.converse(
                modelId=self._model_id,
                messages=[{
                    "role": "user",
                    "content": [{"text": prompt}],
                }],
                inferenceConfig={
                    "temperature": 0.0,
                    "maxTokens": 10,
                },
            )

        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        text = ""
        for block in content_blocks:
            if "text" in block:
                text += block["text"]

        try:
            return float(text.strip())
        except ValueError as error:
            logger.error(f"Judge score parsing failed: {error}")
            return 0.0

    @staticmethod
    def _build_user_prompt(context: str, question: str) -> str:
        return f"""CONTEXT:
{context}

USER QUESTION:
{question}
"""

    async def validate_model(self) -> None:
        async with self._session.client(
            "bedrock-runtime",
            region_name=settings.AWS_REGION,
        ) as client:
            response = await client.converse(
                modelId=self._model_id,
                messages=[{
                    "role": "user",
                    "content": [{"text": "Reply with OK"}],
                }],
                inferenceConfig={
                    "temperature": 0.0,
                    "maxTokens": 8,
                },
            )

        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        text = "".join(
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict)
        ).strip()

        if not text:
            raise AppException(
                message="Chat model validation failed: empty response.",
                status_code=500,
                err_code=ErrorCodes.INTERNAL_SERVER_ERROR,
            )

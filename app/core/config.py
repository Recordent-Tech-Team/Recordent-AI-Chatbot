from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "recordent-chatbot"
    APP_ENV: str = "dev"
    APP_PORT: int = 8000
    APP_DEBUG: bool = False

    CHAT_API_SECRET: str = ""
    ADMIN_API_SECRET: str = ""

    AWS_REGION: str = "us-east-1"
    AWS_PROFILE: str = ""

    BEDROCK_CHAT_MODEL_ID: Literal[
        "us.meta.llama3-3-70b-instruct-v1:0"
    ]
    BEDROCK_EMBEDDING_MODEL_ID: Literal[
        "amazon.titan-embed-text-v2:0"
    ]
    BEDROCK_EMBEDDING_DIMENSION: int = 1024
    BEDROCK_EMBEDDING_MAX_CONCURRENCY: int = 1
    BEDROCK_EMBEDDING_MAX_RETRIES: int = 3
    BEDROCK_EMBEDDING_BASE_BACKOFF_SECONDS: float = 0.7
    BEDROCK_EMBEDDING_REQUEST_INTERVAL_SECONDS: float = 1.0

    S3_BUCKET_NAME: str = ""
    S3_CHATBOT_DOCUMENT_PREFIX: str = "chatbot/documents/"
    S3_CHATBOT_ARCHIVE_PREFIX: str = "chatbot/archive/"

    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = ""
    POSTGRES_USERNAME: str = ""
    POSTGRES_PASSWORD: str = ""
    DATABASE_URL: str = ""
    DB_SCHEMA: str = "dev_ai_chatbot"
    DB_TABLES: list[str] = [
        "chat_sessions",
        "chat_messages",
        "document_versions",
        "documents",
        "embeddings",
        "embedding_archives",
        "audit_logs",
        "evaluation_logs",
    ]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Prefer values from .env over inherited process variables.
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 5

    CHAT_MAX_HISTORY_MESSAGES: int = 10
    CHAT_EVALUATION_ENABLED: bool = False

    LOG_LEVEL: str = "INFO"

    SYSTEM_PROMPT_PATH: str = "app/prompts/system_prompt.txt"

    @property
    def postgres_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USERNAME}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    @property
    def postgres_url_sync(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USERNAME}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

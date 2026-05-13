from openai import AzureOpenAI
from app.core.config import settings

embedding_client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY_RECORDENT_EMBEDDING,
    api_version=settings.AZURE_OPENAI_API_VERSION_RECORDENT_EMBEDDING,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT_RECORDENT_EMBEDDING
)

chat_client = AzureOpenAI(
    api_key=settings.AZURE_OPENAI_API_KEY_RECORDENT_CHAT,
    api_version=settings.AZURE_OPENAI_API_VERSION_RECORDENT_CHAT,
    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT_RECORDENT_CHAT
)
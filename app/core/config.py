import os
from dotenv import load_dotenv
load_dotenv()

class Settings:

    # API SECURITY
    RECORDENT_BACKEND_KEY = os.getenv(
        "RECORDENT_BACKEND_KEY"
    )

    # AZURE OPENAI EMBEDDING
    AZURE_OPENAI_API_KEY_RECORDENT_EMBEDDING = os.getenv(
        "AZURE_OPENAI_API_KEY_RECORDENT_EMBEDDING"
    )
    AZURE_OPENAI_API_VERSION_RECORDENT_EMBEDDING = os.getenv(
        "AZURE_OPENAI_API_VERSION_RECORDENT_EMBEDDING"
    )
    AZURE_OPENAI_ENDPOINT_RECORDENT_EMBEDDING = os.getenv(
        "AZURE_OPENAI_ENDPOINT_RECORDENT_EMBEDDING"
    )
    AZURE_OPENAI_DEPLOYMENT_RECORDENT_EMBEDDING = os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_RECORDENT_EMBEDDING"
    )

    # AZURE OPENAI CHAT
    AZURE_OPENAI_API_KEY_RECORDENT_CHAT = os.getenv(
        "AZURE_OPENAI_API_KEY_RECORDENT_CHAT"
    )
    AZURE_OPENAI_API_VERSION_RECORDENT_CHAT = os.getenv(
        "AZURE_OPENAI_API_VERSION_RECORDENT_CHAT"
    )
    AZURE_OPENAI_ENDPOINT_RECORDENT_CHAT = os.getenv(
        "AZURE_OPENAI_ENDPOINT_RECORDENT_CHAT"
    )
    AZURE_OPENAI_DEPLOYMENT_RECORDENT_CHAT = os.getenv(
        "AZURE_OPENAI_DEPLOYMENT_RECORDENT_CHAT"
    )

    # PATHS
    DATA_PATH = (
        "app/data/raw/"
        "Recordent_Chatbot_Training_Document.docx"
    )
    VECTOR_PATH = (
        "app/vector_store/faiss/index.faiss"
    )
    CHUNKS_PATH = (
        "app/vector_store/metadata/chunks.pkl"
    )

settings = Settings()
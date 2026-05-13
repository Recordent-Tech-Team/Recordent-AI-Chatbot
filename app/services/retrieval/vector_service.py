import os
import pickle
import faiss
from app.core.config import settings
from app.core.logger import get_logger
logger = get_logger("vector_service.py")

index = None
chunks = []
try:
    if os.path.exists(settings.VECTOR_PATH):
        index = faiss.read_index(
            settings.VECTOR_PATH
        )

    else:
        logger.error("FAISS index file not found")

    if os.path.exists(settings.CHUNKS_PATH):
        with open(
            settings.CHUNKS_PATH,
            "rb"
        ) as file:
            chunks = pickle.load(file)

    else:
        logger.error("Chunks metadata file not found")

except Exception as error:
    logger.error(
        f"Vector store loading failed: {str(error)}"
    )
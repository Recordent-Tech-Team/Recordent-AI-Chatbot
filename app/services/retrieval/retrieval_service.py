import numpy as np
import faiss
from app.clients.openai_client import embedding_client
from app.services.retrieval.vector_service import (
    index,
    chunks
)
from app.core.config import settings
from app.core.logger import get_logger
logger = get_logger("retrieval_service.py")

def retrieve(
    query,
    k=8
):
    try:
        if not query:
            logger.error("Empty query received")
            return []

        if index is None:
            logger.error("FAISS index not loaded")
            return []

        if not chunks:
            logger.error("Chunks metadata not loaded")
            return []

        response = embedding_client.embeddings.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_RECORDENT_EMBEDDING,
            input=query
        )

        query_vector = np.array(
            [response.data[0].embedding],
            dtype="float32"
        )

        faiss.normalize_L2(query_vector)
        distances, indexes = index.search(
            query_vector,
            k
        )

        return [
            chunks[i]
            for i in indexes[0]
            if i < len(chunks)
        ]

    except Exception as error:
        logger.error(
            f"Retrieval failed: {str(error)}"
        )
        return []
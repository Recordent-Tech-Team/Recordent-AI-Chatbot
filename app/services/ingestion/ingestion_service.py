import os
import pickle
import faiss
import numpy as np
from docx import Document
from app.core.config import settings
from app.core.logger import get_logger
from app.clients.openai_client import embedding_client
from app.services.ingestion.chunking_service import chunk_text
logger = get_logger("ingestion_service.py")

def load_document():
    try:
        if not os.path.exists(settings.DATA_PATH):
            logger.error("Training document not found")
            return None

        doc = Document(settings.DATA_PATH)
        text = "\n".join(
            [
                p.text
                for p in doc.paragraphs
                if p.text.strip()
            ]
        )

        if not text:
            logger.error("Document content is empty")
            return None

        return text

    except Exception as error:
        logger.error(
            f"Document loading failed: {str(error)}"
        )
        return None


def build_index(force_rebuild=False):
    try:
        if (
            os.path.exists(settings.VECTOR_PATH)
            and not force_rebuild
        ):
            logger.info("FAISS index already exists")
            return {
                "status": True,
                "message": "Index already exists"
            }

        text = load_document()
        if not text:
            return {
                "status": False,
                "message": "Document loading failed"
            }

        chunks = chunk_text(text)
        if not chunks:
            return {
                "status": False,
                "message": "Chunk generation failed"
            }

        response = embedding_client.embeddings.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_RECORDENT_EMBEDDING,
            input=chunks
        )

        embeddings = np.array(
            [item.embedding for item in response.data],
            dtype="float32"
        )

        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)

        os.makedirs(
            "app/vector_store/faiss",
            exist_ok=True
        )
        os.makedirs(
            "app/vector_store/metadata",
            exist_ok=True
        )

        faiss.write_index(
            index,
            settings.VECTOR_PATH
        )

        with open(
            settings.CHUNKS_PATH,
            "wb"
        ) as file:
            pickle.dump(chunks, file)

        return {
            "status": True,
            "message": "Index built successfully",
            "chunks": len(chunks)
        }

    except Exception as error:
        logger.error(
            f"Index build failed: {str(error)}"
        )
        return {
            "status": False,
            "message": "Index build failed"
        }
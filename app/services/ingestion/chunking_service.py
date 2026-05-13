from app.core.logger import get_logger
logger = get_logger("chunking_service.py")

def chunk_text(
    text,
    chunk_size=1000,
    overlap=200
):
    try:
        if not text:
            logger.error("Empty text received for chunking")
            return []

        chunks = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = start + chunk_size
            chunks.append(
                text[start:end]
            )
            start = end - overlap
        return chunks

    except Exception as error:
        logger.error(
            f"Chunking failed: {str(error)}"
        )
        return []
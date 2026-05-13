import os
from app.core.config import settings
from app.core.logger import get_logger
from app.services.retrieval.retrieval_service import retrieve
from app.services.llm.openai_service import generate_answer
logger = get_logger("chatbot_service.py")

def start_chat(question):
    try:
        if not os.path.exists(settings.VECTOR_PATH):
            logger.error("FAISS index not found")
            return {
                "status": False,
                "message": "Index not built yet"
            }
        logger.info(f"Processing question: {question}")
        context = retrieve(question)
        if not context:
            logger.error("No relevant context found")
            return {
                "status": False,
                "message": "No relevant context found"
            }
        
        answer = generate_answer(
            context,
            question
        )
        return {
            "status": True,
            "message": "Success",
            "data": {
                "question": question,
                "answer": answer
            }
        }

    except Exception as error:
        logger.error(
            f"Chat processing failed: {str(error)}"
        )
        return {
            "status": False,
            "message": "Chat processing failed"
        }
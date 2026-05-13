from app.core.logger import get_logger
logger = get_logger("prompt_builder.py")

def build_chat_prompt(
    context,
    question
):
    try:
        return f"""
            CONTEXT:
            {context}

            USER QUESTION:
            {question}
        """

    except Exception as error:
        logger.error(
            f"Prompt building failed: {str(error)}"
        )
        return ""
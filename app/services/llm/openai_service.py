from app.clients.openai_client import chat_client
from app.core.config import settings
from app.core.logger import get_logger
from app.services.llm.prompt_builder import build_chat_prompt
logger = get_logger("openai_service.py")

try:
    with open(
        "app/prompts/system_prompt.txt",
        "r",
        encoding="utf-8"
    ) as file:
        SYSTEM_PROMPT = file.read()

except Exception as error:
    logger.error(
        f"System prompt loading failed: {str(error)}"
    )
    SYSTEM_PROMPT = ""

def generate_answer(
    context_chunks,
    question
):
    try:
        if not context_chunks:
            logger.error("Context chunks are empty")
            return None

        context = "\n\n".join(context_chunks)
        user_prompt = build_chat_prompt(
            context=context,
            question=question
        )

        response = chat_client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_RECORDENT_CHAT,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.2,
            max_tokens=800
        )

        answer = response.choices[0].message.content
        if not answer:
            logger.error("Empty AI response received")
            return None
        return answer

    except Exception as error:
        logger.error(
            f"AI response generation failed: {str(error)}"
        )
        return None
import os
from openai import OpenAI
from app.utils.logger import logger

API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing")

client = OpenAI(api_key=API_KEY)


async def run_chat_completion(messages: list) -> str:
    """
    Unified call for OpenAI chat completions.
    """
    try:
        logger.info("[OPENAI] Request started")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4,
            max_tokens=8000
        )

        logger.info("[OPENAI] Request completed")

        return response.choices[0].message["content"]

    except Exception as e:
        logger.error(f"[OPENAI] Error: {e}")
        raise

# app/services/openai_client.py

from openai import AsyncOpenAI
from app.utils.logger import logger

client = AsyncOpenAI()   # API key is taken from env OPENAI_API_KEY


async def run_chat_completion(messages: list, model: str = "gpt-4.1"):
    """
    Run async chat completion and return text content.
    """

    logger.info(f"[OpenAI] Calling model={model}")

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.4,
            max_tokens=4096
        )

        return resp.choices[0].message.content

    except Exception as e:
        logger.error(f"[OpenAI] ChatCompletion error: {e}")
        raise

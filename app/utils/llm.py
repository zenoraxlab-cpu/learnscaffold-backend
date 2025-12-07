import os
import openai

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL

openai.api_key = OPENAI_API_KEY
openai.base_url = OPENAI_BASE_URL


async def run_gpt(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Unified GPT call wrapper used by structure_extractor.
    Ensures stable interface for all LLM-related tasks.
    """

    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert document analyst."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000,
            temperature=0.2,
        )

        return response.choices[0].message["content"]

    except Exception as e:
        raise RuntimeError(f"LLM error: {str(e)}")

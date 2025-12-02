import json
import re
from openai import OpenAI
from app.utils.logger import logger
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL


# ---------------------------------------------------------
# Init OpenAI client with explicit config
# ---------------------------------------------------------
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)


def cleanup_json(text: str) -> str:
    """
    Removes markdown fences such as ```json ... ``` purely.
    Leaves clean JSON ready for json.loads().
    """
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()


def classify_document(chunk: str) -> dict:
    """
    Classify document by providing LLM with a short text chunk.
    Must return long JSON with:
      - document_type
      - main_topics[]
      - level
      - summary
      - recommended_days
    """

    logger.info("[CLASSIFIER] Starting LLM classification")

    prompt = f"""
Analyze the following text and return STRICT JSON.

TEXT:
\"\"\"{chunk[:4000]}\"\"\"

FORMAT:
{{
  "document_type": "...",
  "main_topics": ["...", "..."],
  "level": "beginner | intermediate | advanced",
  "summary": "...",
  "recommended_days": 0
}}

Return ONLY JSON. No markdown.
"""

    # -----------------------------------------------------
    # NEW OpenAI Responses API
    # -----------------------------------------------------
    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": "You are an expert education analyst. Always return strict, valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_output_tokens=600,
            temperature=0.2,
        )
    except Exception as e:
        logger.error(f"[CLASSIFIER] LLM request failed: {e}")
        raise RuntimeError("LLM request failed") from e

    # -----------------------------------------------------
    # Extract text — only valid field for Responses API
    # -----------------------------------------------------
    try:
        raw_output: str = resp.output_text
    except Exception as e:
        logger.error(f"[CLASSIFIER] Could not read resp.output_text: {e}")
        raise ValueError("Invalid LLM response") from e

    if not raw_output or not raw_output.strip():
        logger.error("[CLASSIFIER] LLM returned empty output")
        raise ValueError("Empty LLM output")

    logger.info(f"[CLASSIFIER] Raw output (200 chars): {raw_output[:200]}")

    # Clean markdown fences
    cleaned = cleanup_json(raw_output)

    # -----------------------------------------------------
    # Parse JSON strictly
    # -----------------------------------------------------
    try:
        result = json.loads(cleaned)
    except Exception as e:
        logger.error(f"[CLASSIFIER] JSON parse error: {e}")
        logger.error(f"[CLASSIFIER] CLEANED JSON:\n{cleaned}")
        raise ValueError("Failed to parse JSON from LLM") from e

    logger.info("[CLASSIFIER] Classification completed")

    return result

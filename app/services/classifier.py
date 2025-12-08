import json
import time
import re
from typing import List
from openai import OpenAI

from app.utils.logger import logger
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL


# =========================================================
# OpenAI client
# =========================================================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# Модель: сбалансированная, стабильная, без частых 429
MODEL = "gpt-4.1-mini"


# =========================================================
# Helpers
# =========================================================

def cleanup_json(text: str) -> str:
    """Remove ```json fences and return pure JSON."""
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)
    return text.strip()


def merge_chunks(chunks: List[str], max_chars: int = 20000) -> str:
    """
    Берём первые чанки текста, пока не превысили лимит,
    чтобы не перегружать модель, но дать контекст.
    """
    combined = []
    total = 0

    for c in chunks:
        if total + len(c) > max_chars:
            break
        combined.append(c)
        total += len(c)

    return "\n\n".join(combined)


# =========================================================
# MAIN CLASSIFIER
# =========================================================

def classify_document(chunks: List[str]) -> dict:
    """
    Stable classifier:
      - merges multiple chunks (до ~20k символов)
      - retries on 429
      - guaranteed JSON output
    """

    logger.info("[CLASSIFIER] Starting LLM classification")

    if not chunks:
        raise ValueError("No text chunks provided")

    text_sample = merge_chunks(chunks)

    prompt = f"""
Analyze the following text and return STRICT JSON.

TEXT:
\"\"\"{text_sample[:20000]}\"\"\"


REQUIRED JSON FORMAT:
{{
  "document_type": "...",
  "main_topics": ["...", "..."],
  "level": "beginner | intermediate | advanced",
  "summary": "...",
  "recommended_days": 1
}}

Rules:
- Return ONLY JSON.
- No markdown.
- No comments.
- Do not hallucinate content not present in the text.
"""

    # ===============================
    # Retry loop for stability (429)
    # ===============================
    attempts = 3
    for attempt in range(1, attempts + 1):

        try:
            resp = client.responses.create(
                model=MODEL,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert educational analyst. "
                            "Always return strict, valid JSON, without markdown."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                max_output_tokens=800,
                temperature=0.2,
            )

            raw = resp.output_text
            logger.info(f"[CLASSIFIER] Raw output (200 chars): {raw[:200]}")

            if not raw:
                raise ValueError("Empty LLM output")

            cleaned = cleanup_json(raw)

            result = json.loads(cleaned)
            logger.info("[CLASSIFIER] Classification completed")

            return result

        except Exception as e:
            logger.error(f"[CLASSIFIER] Attempt {attempt}/{attempts} failed: {e}")

            # RATE LIMIT → wait & retry
            if "rate limit" in str(e).lower() or "429" in str(e):
                wait_sec = 5 * attempt
                logger.error(f"[CLASSIFIER] Rate limit hit → waiting {wait_sec}s...")
                time.sleep(wait_sec)
                continue

            if attempt == attempts:
                raise RuntimeError("LLM classification failed after retries") from e

            # short wait for other transient errors
            time.sleep(2)

    # Should never reach here
    raise RuntimeError("Unexpected classifier error")

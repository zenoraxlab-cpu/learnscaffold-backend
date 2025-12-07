from app.utils.llm import run_gpt
from app.utils.logger import logger

def extract_structure(text: str, classification: dict) -> list:
    """
    Build study structure from cleaned text and classification metadata.
    """

    logger.info("[STRUCTURE] Starting structure extraction")

    # Формируем безопасный промпт
    prompt = f"""
You are an expert in academic document structure analysis.

Given the following text (cleaned OCR output) and classification metadata,
identify the logical structure of the document. Return JSON only.

CLASSIFICATION:
{classification}

TEXT:
{text[:4000]}  # truncate to avoid overload

Return strictly this JSON format:

[
  {{
    "title": "Section name",
    "level": 1,
    "page_start": null,
    "page_end": null
  }}
]
"""

    try:
        raw = run_gpt(prompt, max_tokens=800)
        logger.info("[STRUCTURE] Raw LLM output received")

        import json
        structure = json.loads(raw)

        if not isinstance(structure, list):
            logger.error("[STRUCTURE] Output is not a list")
            return []

        return structure

    except Exception as e:
        logger.error(f"[STRUCTURE] ERROR: {e}")
        return []

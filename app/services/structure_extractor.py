from app.utils.llm import run_gpt
from app.utils.logger import logger


async def extract_structure(cleaned_text: str, classification: dict):
    """
    Extracts document structure using GPT.
    Returns a list of sections.
    """

    logger.info("[STRUCTURE] Starting structure extraction")

    prompt = f"""
You are a system that extracts clean document structure.

Input text (cleaned):
\"\"\"{cleaned_text[:6000]}\"\"\"

Document type: {classification.get("document_type")}
Main topics: {classification.get("main_topics")}

TASK:
Return ONLY JSON list of sections. Example:

[
  {{
    "title": "Chapter 1. Introduction",
    "topics": ["topic A", "topic B"]
  }},
  {{
    "title": "Chapter 2. Logic Basics",
    "topics": ["topic C"]
  }}
]

Rules:
- No explanations.
- No markdown.
- MUST be valid JSON.
"""

    try:
        raw = await run_gpt(prompt, model="gpt-4o-mini")

        logger.info(f"[STRUCTURE] Raw model output (first 200 chars): {raw[:200]}")

        # Try to parse JSON
        import json
        data = json.loads(raw)

        if isinstance(data, list):
            return data
        else:
            logger.warning("[STRUCTURE] Model returned non-list, wrapping")
            return list(data)

    except Exception as e:
        logger.error(f"[STRUCTURE] ERROR: {e}")
        # Fail gracefully — structure is optional
        return []

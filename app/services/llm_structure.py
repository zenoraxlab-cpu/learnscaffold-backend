import json
from app.utils.logger import logger
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You extract document structure from raw text. 
Your output must be JSON only.

Return list of objects:
[
  {
    "title": "Chapter name",
    "pages": [1,2],
    "topics": ["topic1", "topic2"]
  }
]

If you cannot determine pages, leave empty list.
Do NOT create artificial content. Only use what appears in the text.
"""

def extract_structure_llm(full_text: str, language: str = "en"):
    """
    Fallback LLM structure extractor for OCR PDFs.
    """
    logger.warning("[LLM_STRUCTURE] Fallback structure extraction activated")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Document language = {language}. Extract structure: "
                        f"ONLY JSON. No markdown. No comments.\n\n"
                        f"{full_text[:6000]}"
                    ),
                },
            ],
            temperature=0.1,
        )

        raw = response.choices[0].message.content.strip()
        logger.warning(f"[LLM_STRUCTURE RAW] {raw[:300]}")

        # ----------------------------------------------------
        # CLEAN MARKDOWN (```json ... ```)
        # ----------------------------------------------------
        cleaned = (
            raw.replace("```json", "")
               .replace("```", "")
               .replace("```JSON", "")
               .strip()
        )

        # Log cleaned JSON to debug
        logger.warning(f"[LLM_STRUCTURE CLEANED] {cleaned[:300]}")

        # Parse JSON
        structure = json.loads(cleaned)

        # Guarantee correct type
        if not isinstance(structure, list):
            logger.error("[LLM_STRUCTURE] Not a list → return empty list")
            return []

        return structure

    except Exception as e:
        logger.error(f"[LLM_STRUCTURE ERROR] {e}")
        return []

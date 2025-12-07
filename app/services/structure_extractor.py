from app.utils.llm import run_gpt
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_pages
import json


async def extract_structure(file_path: str):
    """
    Extracts semantic structure of a PDF with page numbers.
    Returns list of sections:
    [
        {
            "title": "...",
            "topics": [...],
            "pages": [3,4,5]
        }
    ]
    """

    logger.info("[STRUCTURE] Starting PDF-based structure extraction")

    # 1. Load pages
    try:
        pages = await extract_pdf_pages(file_path)
    except Exception as e:
        logger.error(f"[STRUCTURE] Page extraction failed: {e}")
        return []

    if not pages or len(pages) == 0:
        logger.warning("[STRUCTURE] No pages extracted")
        return []

    # Limit text to avoid overloading GPT
    MAX_PAGES = 12
    sampled = pages[:MAX_PAGES]

    # Build unified text with page markers
    page_joined = "\n\n".join(
        f"=== PAGE {i+1} ===\n{content}"
        for i, content in enumerate(sampled)
    )

    prompt = f"""
You extract the semantic structure of a PDF textbook.

Below is the document content with explicit PAGE markers.
Use these page numbers to assign pages to each section.

Return ONLY JSON list of sections:
[
  {{
    "title": "Chapter 1. Introduction",
    "topics": ["logic", "thinking"],
    "pages": [1, 2, 3]
  }},
  {{
    "title": "Japanese Crosswords",
    "topics": ["puzzles", "logic"],
    "pages": [7, 8]
  }}
]

Rules:
- MUST be valid JSON.
- Pages MUST be integers.
- Pages correspond to the PAGE markers you see.
- Do NOT invent pages outside the provided range.
- No commentary, no markdown.

Document text:
\"\"\" 
{page_joined}
\"\"\"
"""

    try:
        raw = await run_gpt(prompt, model="gpt-4o-mini")
        logger.info(f"[STRUCTURE] Raw output (first 200 chars): {raw[:200]}")

        data = json.loads(raw)

        if isinstance(data, list):
            return data

        # fallback
        return list(data)

    except Exception as e:
        logger.error(f"[STRUCTURE] ERROR: {e}")
        return []

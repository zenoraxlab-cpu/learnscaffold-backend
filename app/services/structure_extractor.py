from app.utils.llm import run_gpt
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_pages
import json


MAX_PAGES = 3                # используем только первые 3 страницы
MAX_CHARS_PER_PAGE = 2000    # ограничиваем размер каждой страницы
MAX_TOTAL_PROMPT = 7000      # общий предел текста для GPT


async def extract_structure(file_path: str):
    """
    Extract semantic structure with page numbers,
    but optimized to avoid memory spikes.
    """

    logger.info("[STRUCTURE] Starting structure extraction")

    # 1. Load PDF pages
    try:
        pages = await extract_pdf_pages(file_path)
    except Exception as e:
        logger.error(f"[STRUCTURE] Page extraction failed: {e}")
        return []

    if not pages:
        logger.warning("[STRUCTURE] No pages extracted")
        return []

    # 2. Take only the first few pages
    sampled = pages[:MAX_PAGES]

    # 3. Trim each page to avoid huge payloads
    trimmed_pages = []
    for i, content in enumerate(sampled):
        if not content:
            continue
        trimmed = content[:MAX_CHARS_PER_PAGE]
        trimmed_pages.append(f"=== PAGE {i+1} ===\n{trimmed}")

    # 4. Build limited document text
    page_joined = "\n\n".join(trimmed_pages)

    # Hard trim global size
    if len(page_joined) > MAX_TOTAL_PROMPT:
        page_joined = page_joined[:MAX_TOTAL_PROMPT]

    logger.info(f"[STRUCTURE] Prompt size: {len(page_joined)} chars")

    prompt = f"""
Extract semantic structure of the textbook.

Return ONLY JSON list of sections:
[
  {{
    "title": "...",
    "topics": ["..."],
    "pages": [1, 2]
  }}
]

Rules:
- MUST be valid JSON.
- Pages must correspond only to PAGE markers below.
- No commentary.

Document:
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

        return list(data)

    except Exception as e:
        logger.error(f"[STRUCTURE] ERROR: {e}")
        return []

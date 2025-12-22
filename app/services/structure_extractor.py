import fitz
import re
from app.utils.logger import logger


# =========================================================
# 1. Extract structure from PDF visually (PyMuPDF)
# =========================================================
def extract_structure(path: str):
    """
    Extracts semantic structure from PDF using PyMuPDF.
    Returns a list of blocks:
    {
        "title": "...",
        "topics": [],
        "pages": [page_number]
    }
    """

    logger.info(f"[STRUCTURE] Extracting structure from: {path}")

    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.error(f"[STRUCTURE] Cannot open PDF: {e}")
        return []

    structure = []

    try:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            lines = text.splitlines()

            for line in lines:
                clean = line.strip()

                if (
                    5 < len(clean) < 80
                    and clean[0].isupper()
                    and not clean.endswith(".")
                ):
                    structure.append({
                        "title": clean,
                        "topics": [],
                        "pages": [page_num]
                    })

    except Exception as e:
        logger.error(f"[STRUCTURE] Error parsing structure: {e}")
        return []

    finally:
        doc.close()

    logger.info(f"[STRUCTURE] Found PDF headings: {len(structure)}")
    return structure


# =========================================================
# 2. Extract structure from plain text (OCR / text fallback)
# =========================================================
def extract_structure_from_text(text_by_page: list) -> list:
    """
    Extract structure from text.
    Expects:
      text_by_page = [{ "page": int, "text": str }, ...]
    GUARANTEES non-empty result.
    """

    logger.warning("[STRUCTURE] Running text-based structure extractor")

    structure = []
    seen_titles = set()

    chapter_regex = re.compile(
        r"(?i)\b(глава|chapter|section)\s+\d{1,3}[:\.\-]?\s+([A-Za-zА-Яа-яЁё0-9 ,\-]{3,100})"
    )

    numbered_regex = re.compile(
        r"^\s*\d{1,3}(\.\d{1,3})*\s+[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9 ,\-]{3,100}$"
    )

    simple_header_regex = re.compile(
        r"^[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9 ,\-]{5,80}$"
    )

    for item in text_by_page:
        page = item.get("page", 1)
        text = item.get("text") or ""

        if not text or len(text) < 20:
            continue

        # Pattern 1 — Chapter-like
        for match in chapter_regex.findall(text):
            title = match[1].strip()
            if title and title not in seen_titles:
                structure.append({
                    "title": title,
                    "topics": [],
                    "pages": [page]
                })
                seen_titles.add(title)

        # Pattern 2 — Numbered headings
        for line in text.splitlines():
            clean = line.strip()
            if numbered_regex.match(clean) and clean not in seen_titles:
                structure.append({
                    "title": clean,
                    "topics": [],
                    "pages": [page]
                })
                seen_titles.add(clean)

        # Pattern 3 — Simple headers
        for line in text.splitlines():
            clean = line.strip()
            if 5 < len(clean) < 80 and simple_header_regex.match(clean):
                if clean not in seen_titles:
                    structure.append({
                        "title": clean,
                        "topics": [],
                        "pages": [page]
                    })
                    seen_titles.add(clean)

    # =====================================================
    # HARD FALLBACK — NEVER RETURN EMPTY STRUCTURE
    # =====================================================
    if not structure:
        logger.error("[STRUCTURE] Empty result → fallback by pages")

        for item in text_by_page:
            page = item.get("page", 1)
            text = (item.get("text") or "").strip()
            if not text:
                continue

            structure.append({
                "title": f"Page {page}",
                "topics": [],
                "pages": [page]
            })

    logger.info(f"[STRUCTURE] Final structure size: {len(structure)}")
    return structure

import fitz
import re
from app.utils.logger import logger


# =========================================================
# 1. Extract structure from PDF visually (your original)
# =========================================================
def extract_structure(path: str):
    """
    Extracts REAL semantic structure from PDF using PyMuPDF.
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

                # Heuristic: possible section title
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
# 2. Extract structure from plain text (regex-based fallback)
# =========================================================
def extract_structure_from_text(text_by_page: list) -> list:
    """
    Fallback structure extractor for plain text (after OCR or simple PDFs).
    Expects text_by_page = [{ "page": int, "text": str }, ...]
    """

    logger.warning("[STRUCTURE_FALLBACK] Running regex-based structure extractor")

    structure = []
    seen_titles = set()

    # Pattern 1 — Глава / Chapter / Section
    chapter_regex = re.compile(
        r"(?i)\b(глава|chapter|section)\s+\d{1,3}[:\.\-]?\s+([A-Za-zА-Яа-яЁё0-9 ,\-]{3,100})"
    )

    # Pattern 2 — numbered headings "1.2 Title", "2 Introduction"
    numbered_regex = re.compile(
        r"^\s*\d{1,3}(\.\d{1,3})*\s+[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9 ,\-]{3,100}$",
        re.MULTILINE
    )

    # Pattern 3 — isolated capitalized headings
    simple_header_regex = re.compile(
        r"^[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё0-9 ,\-]{5,80}$",
        re.MULTILINE
    )

    for item in text_by_page:
        page = item["page"]
        text = item["text"]

        if not text or len(text) < 20:
            continue

        # --- Pattern 1: Chapter-like headings ---
        for match in chapter_regex.findall(text):
            raw_title = match[1].strip()
            if raw_title and raw_title not in seen_titles:
                structure.append({
                    "title": raw_title,
                    "topics": [],
                    "pages": [page]
                })
                seen_titles.add(raw_title)

        # --- Pattern 2: Numbered headings ---
        for match in numbered_regex.findall(text):
            # match returns only subgroups — extract full match differently
            for line in text.splitlines():
                if numbered_regex.match(line.strip()):
                    title = line.strip()
                    if title not in seen_titles:
                        structure.append({
                            "title": title,
                            "topics": [],
                            "pages": [page]
                        })
                        seen_titles.add(title)

        # --- Pattern 3: Simple isolated headings ---
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

    logger.warning(f"[STRUCTURE_FALLBACK] Extracted text-based chapters: {len(structure)}")
    return structure

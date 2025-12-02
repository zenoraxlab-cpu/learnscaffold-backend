# app/services/structure_extractor.py

import fitz
from app.utils.logger import logger

def extract_structure(path: str):
    """
    Extracts headings/chapters using simple heuristics from PDF text.
    Fully synchronous — NO async calls inside.
    """
    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.error(f"[STRUCTURE] Failed to open PDF: {e}")
        return []

    structure = []

    try:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            lines = text.splitlines()

            for line in lines:
                line_clean = line.strip()

                # Simple naive heuristic:
                if (
                    len(line_clean) > 3
                    and len(line_clean) < 80
                    and line_clean[0].isupper()
                    and (line_clean.endswith(".") is False)
                ):
                    structure.append({
                        "page": page_num,
                        "title": line_clean
                    })

    except Exception as e:
        logger.error(f"[STRUCTURE] Error: {e}")
        return []

    finally:
        doc.close()

    logger.info(f"[STRUCTURE] Units found: {len(structure)}")
    return structure

import fitz
from app.utils.logger import logger

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

    logger.info(f"[STRUCTURE] Found headings: {len(structure)}")
    return structure

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_pages
from app.services.pdf_extractor import extract_pdf_text_sync


def extract_clean_text(pdf_path: str) -> list:
    """
    SYNC function.
    Returns:
      [{ "page": int, "text": str }, ...]
    """

    logger.info(f"[PDF_TEXT] extract_clean_text: {pdf_path}")

    try:
        # 1. extract pages metadata (sync)
        pages = extract_pdf_pages(pdf_path)

        # 2. extract text (SYNC VERSION ONLY)
        text_by_page = extract_pdf_text_sync(pdf_path)

        if not isinstance(text_by_page, list):
            raise ValueError("extract_pdf_text_sync returned invalid data")

        logger.info(f"[PDF_TEXT] Text cleaning finished, pages={len(text_by_page)}")
        return text_by_page

    except Exception as e:
        logger.error(f"[PDF_TEXT] Failed: {e}")
        return []

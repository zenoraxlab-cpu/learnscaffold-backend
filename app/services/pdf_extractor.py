import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader
from app.utils.logger import logger


# ============================================================
# 1) Извлечение всего текста PDF
# ============================================================

def extract_pdf_text(path: str) -> str:
    """
    Основная функция извлечения всего текста PDF.
    Порядок:
    1) PyMuPDF
    2) pdfplumber
    3) PyPDF2 (fallback)
    """

    logger.info(f"[PDF] extract_pdf_text(): starting for {path}")

    text = ""

    # ---------------------------------------------------------
    # 1) PyMuPDF — лучший и самый надежный вариант
    # ---------------------------------------------------------
    try:
        doc = fitz.open(path)
        logger.info(f"[PDF] PyMuPDF opened document, pages={len(doc)}")

        for page in doc:
            text += page.get_text("text") + "\n"

        doc.close()

        if len(text.strip()) > 20:
            logger.info("[PDF] Extracted via PyMuPDF successfully")
            return text

        logger.warning("[PDF] PyMuPDF returned too little text, fallback to pdfplumber")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF failed: {e}")

    # ---------------------------------------------------------
    # 2) pdfplumber
    # ---------------------------------------------------------
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

        if len(text.strip()) > 20:
            logger.info("[PDF] Extracted via pdfplumber successfully")
            return text

        logger.warning("[PDF] pdfplumber returned too little text, fallback to PyPDF2")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # ---------------------------------------------------------
    # 3) PyPDF2 — последний fallback
    # ---------------------------------------------------------
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if len(text.strip()) > 20:
            logger.info("[PDF] Extracted via PyPDF2 successfully")
            return text

        logger.warning("[PDF] PyPDF2 returned too little text")

    except Exception as e:
        logger.error(f"[PDF] PyPDF2 failed: {e}")

    # ---------------------------------------------------------
    # Если всё полностью провалилось
    # ---------------------------------------------------------
    logger.error("[PDF] No text could be extracted by any method")
    return ""


# ============================================================
# 2) Извлечение текста PDF ПОСТРАНИЦЕ
# ============================================================

def extract_pdf_pages(path: str) -> list:
    """
    Возвращает массив страниц вида:
    [
        { "page": 1, "text": "..."},
        { "page": 2, "text": "..."},
        ...
    ]
    """

    logger.info(f"[PDF] extract_pdf_pages(): starting for {path}")

    pages = []

    # ---------------------------------------------------------
    # Пытаемся PyMuPDF
    # ---------------------------------------------------------
    try:
        doc = fitz.open(path)
        logger.info(f"[PDF] PyMuPDF opened document (page-by-page), pages={len(doc)}")

        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append({
                "page": i + 1,
                "text": text.strip() if text else ""
            })

        doc.close()

        if any(p["text"] for p in pages):
            logger.info("[PDF] extract_pdf_pages via PyMuPDF OK")
            return pages

        logger.warning("[PDF] PyMuPDF page extraction returned empty pages")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF pages failed: {e}")

    # ---------------------------------------------------------
    # Пытаемся через pdfplumber
    # ---------------------------------------------------------
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                pages.append({
                    "page": i + 1,
                    "text": text.strip() if text else ""
                })

        if any(p["text"] for p in pages):
            logger.info("[PDF] extract_pdf_pages via pdfplumber OK")
            return pages

        logger.warning("[PDF] pdfplumber returned empty pages")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber pages failed: {e}")

    # ---------------------------------------------------------
    # Пытаемся через PyPDF2
    # ---------------------------------------------------------
    try:
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            pages.append({
                "page": i + 1,
                "text": text.strip() if text else ""
            })

        if any(p["text"] for p in pages):
            logger.info("[PDF] extract_pdf_pages via PyPDF2 OK")
            return pages

        logger.warning("[PDF] PyPDF2 returned empty pages")

    except Exception as e:
        logger.error(f"[PDF] PyPDF2 pages failed: {e}")

    logger.error("[PDF] Could not extract pages with any method")
    return []

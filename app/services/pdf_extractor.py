import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader

from app.utils.logger import logger
from app.services.google_ocr import google_ocr_pdf


# ---------------------------------------------------------
# Detect whether PDF is scanned (no text layer)
# ---------------------------------------------------------
def detect_scanned_pdf(path: str) -> bool:
    try:
        doc = fitz.open(path)
        total_text = 0

        for page in doc:
            t = page.get_text("text")
            if t:
                total_text += len(t)

        doc.close()

        if total_text < 20:
            logger.info("[PDF] No text layer detected → scanned PDF")
            return True

        return False

    except Exception:
        logger.warning("[PDF] detect_scanned_pdf failed → assuming scanned")
        return True


# ---------------------------------------------------------
# ASYNC: Extract text from PDF (with OCR fallback)
# Используется ТОЛЬКО в /analyze/init
# ---------------------------------------------------------
async def extract_pdf_text(path: str) -> str:
    logger.info(f"[PDF] extract_pdf_text (async): {path}")

    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned PDF → Google Vision OCR fallback")
        return await google_ocr_pdf(path)

    # PyMuPDF
    try:
        doc = fitz.open(path)
        text = "\n".join((page.get_text("text") or "") for page in doc)
        doc.close()

        if len(text.strip()) > 20:
            logger.info("[PDF] PyMuPDF OK")
            return text

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF failed: {e}")

    # pdfplumber
    try:
        tmp = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    tmp += t + "\n"

        if len(tmp.strip()) > 20:
            logger.info("[PDF] pdfplumber OK")
            return tmp

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # PyPDF2
    try:
        tmp = ""
        reader = PdfReader(path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                tmp += t + "\n"

        if len(tmp.strip()) > 20:
            logger.info("[PDF] PyPDF2 OK")
            return tmp

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    logger.warning("[PDF] Async OCR fallback")
    return await google_ocr_pdf(path)


# ---------------------------------------------------------
# SYNC: Extract text from PDF (NO OCR)
# Используется в generate / Celery
# ---------------------------------------------------------
def extract_pdf_text_sync(path: str) -> str:
    logger.info(f"[PDF] extract_pdf_text_sync: {path}")

    # PyMuPDF
    try:
        doc = fitz.open(path)
        text = "\n".join((page.get_text("text") or "") for page in doc)
        doc.close()

        if len(text.strip()) > 20:
            return text

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF sync failed: {e}")

    # pdfplumber
    try:
        tmp = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    tmp += t + "\n"

        if len(tmp.strip()) > 20:
            return tmp

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber sync failed: {e}")

    # PyPDF2
    try:
        tmp = ""
        reader = PdfReader(path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                tmp += t + "\n"

        if len(tmp.strip()) > 20:
            return tmp

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 sync failed: {e}")

    logger.warning("[PDF] Sync extraction returned empty text")
    return ""


# ---------------------------------------------------------
# Extract pages (SYNC, без OCR)
# ---------------------------------------------------------
def extract_pdf_pages(path: str) -> list:
    logger.info(f"[PDF] extract_pdf_pages: {path}")

    try:
        doc = fitz.open(path)
        pages = []

        for i, page in enumerate(doc):
            text = (page.get_text("text") or "").strip()
            pages.append({
                "page": i + 1,
                "text": text,
                "ocr_needed": len(text) < 10,
                "image": None
            })

        doc.close()
        logger.info("[PDF] PyMuPDF per-page OK")
        return pages

    except Exception as e:
        logger.warning(f"[PDF] extract_pdf_pages failed: {e}")

    return [{"page": 1, "text": "", "ocr_needed": True, "image": None}]

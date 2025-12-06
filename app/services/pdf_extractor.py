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
# Split extracted OCR text into equal pseudo-pages
# ---------------------------------------------------------
def split_text_into_pages(text: str, page_count: int) -> list:
    if page_count <= 1:
        return [{"page": 1, "text": text}]

    length = len(text)
    chunk = max(1, length // page_count)

    pages = []
    for i in range(page_count):
        start = i * chunk
        end = (i + 1) * chunk

        pages.append({
            "page": i + 1,
            "text": text[start:end].strip(),
        })

    return pages


# ---------------------------------------------------------
# Extract text from PDF (auto fallback to OCR if scanned)
# ---------------------------------------------------------
async def extract_pdf_text(path: str) -> str:
    logger.info(f"[PDF] extract_pdf_text: {path}")

    # SCANNED PDF → OCR
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned PDF → Google Vision OCR fallback")
        return await google_ocr_pdf(path)

    # Method 1: PyMuPDF
    try:
        doc = fitz.open(path)
        text = "\n".join((page.get_text("text") or "") for page in doc)
        doc.close()

        if len(text.strip()) > 20:
            logger.info("[PDF] PyMuPDF OK")
            return text

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF extraction failed: {e}")

    # Method 2: pdfplumber
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
        logger.warning(f"[PDF] pdfplumber extraction failed: {e}")

    # Method 3: PyPDF2
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
        logger.warning(f"[PDF] PyPDF2 extraction failed: {e}")

    # OCR fallback
    logger.warning("[PDF] Switching to Google Vision OCR fallback")
    return await google_ocr_pdf(path)


# ---------------------------------------------------------
# Extract pages with separate text chunks
# ---------------------------------------------------------
def extract_pdf_pages(path: str) -> list:
    logger.info(f"[PDF] extract_pdf_pages: {path}")

    # SCANNED PDF → OCR page splitting
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned PDF → using OCR for pages")

        # OC R is async → вызываем синхронно НЕЛЬЗЯ
        # Поэтому мы пока не используем OCR для страниц
        # Возвращаем пустые тексты, но правильное количество страниц
        doc = fitz.open(path)
        page_count = len(doc)
        doc.close()

        return [
            {
                "page": i + 1,
                "text": "",
                "ocr_needed": True,
                "image": None   # Под OCR page-by-page добавим позже
            }
            for i in range(page_count)
        ]

    # Method 1: PyMuPDF
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
        logger.warning(f"[PDF] PyMuPDF page extraction failed: {e}")

    # Method 2: pdfplumber
    try:
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                pages.append({
                    "page": i + 1,
                    "text": text,
                    "ocr_needed": len(text) < 10,
                    "image": None
                })

        logger.info("[PDF] pdfplumber per-page OK")
        return pages

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber page extraction failed: {e}")

    # Method 3: PyPDF2
    try:
        pages = []
        reader = PdfReader(path)

        for i, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            pages.append({
                "page": i + 1,
                "text": text,
                "ocr_needed": len(text) < 10,
                "image": None
            })

        logger.info("[PDF] PyPDF2 per-page OK")
        return pages

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 page extraction failed: {e}")

    # Fallback: return single empty page
    return [{"page": 1, "text": "", "ocr_needed": True, "image": None}]


def extract_pdf_text_google_ocr(file_path: str) -> str:
    """
    Placeholder for Google OCR extraction.
    Temporarily returns empty string so backend won't crash.
    Later will be replaced with full OCR implementation.
    """
    return ""

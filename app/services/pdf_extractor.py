import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader
import os
import httpx

from app.utils.logger import logger
from app.services.google_ocr import google_ocr_pdf   # <-- GOOGLE OCR
from app.config import GOOGLE_OCR_API_KEY


"""
Unified PDF extraction pipeline:

Order:
1) Detect scanned PDF (no text layer)
2) PyMuPDF
3) pdfplumber
4) PyPDF2
5) Google Vision OCR fallback (async)

APIs:
- extract_pdf_text(path)  -> str
- extract_pdf_pages(path) -> [{page, text}]
"""


# =====================================================================
# DETECT IF PDF IS SCANNED (NO TEXT LAYER)
# =====================================================================

def detect_scanned_pdf(path: str) -> bool:
    """
    Checks if PDF contains no text (images only).
    """
    try:
        doc = fitz.open(path)
        total_text = 0

        for page in doc:
            t = page.get_text("text")
            if t:
                total_text += len(t)

        doc.close()

        if total_text < 20:
            logger.info(f"[PDF] No text layer detected → scanned PDF")
            return True

        return False

    except Exception:
        logger.warning("[PDF] detect_scanned_pdf failed → assuming scanned")
        return True


# =====================================================================
# INTERNAL: SPLIT OCR TEXT INTO PAGES
# =====================================================================

def split_text_into_pages(text: str, page_count: int) -> list:
    """
    Splits OCR text into page_count equal segments.
    """
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
            "text": text[start:end].strip()
        })

    return pages


# =====================================================================
# EXTRACT TEXT (Main function)
# =====================================================================

async def extract_pdf_text(path: str) -> str:
    logger.info(f"[PDF] extract_pdf_text: {path}")

    # --- scanned PDF → OCR immediately ---
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned PDF → Google Vision OCR fallback")
        return await google_ocr_pdf(path)

    # --- PyMuPDF ---
    try:
        doc = fitz.open(path)
        text = "\n".join((page.get_text("text") or "") for page in doc)
        doc.close()

        if len(text.strip()) > 20:
            logger.info("[PDF] PyMuPDF OK")
            return text

        logger.warning("[PDF] PyMuPDF empty → pdfplumber")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF failed: {e}")

    # --- pdfplumber ---
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

        logger.warning("[PDF] pdfplumber empty → PyPDF2")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # --- PyPDF2 ---
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

        logger.warning("[PDF] PyPDF2 empty → OCR fallback")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # --- OCR fallback ---
    logger.warning("[PDF] Switching to Google Vision OCR fallback")
    return await google_ocr_pdf(path)


# =====================================================================
# EXTRACT TEXT PER PAGE
# =====================================================================

async def extract_pdf_pages(path: str) -> list:
    logger.info(f"[PDF] extract_pdf_pages: {path}")

    # --- scanned → OCR immediately ---
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned → Google Vision OCR for pages")

        text = await google_ocr_pdf(path)
        if not text.strip():
            return []

        doc = fitz.open(path)
        page_count = len(doc)
        doc.close()

        return split_text_into_pages(text, page_count)

    # --- PyMuPDF ---
    try:
        doc = fitz.open(path)
        pages = [
            {"page": i + 1, "text": (page.get_text("text") or "").strip()}
            for i, page in enumerate(doc)
        ]
        doc.close()

        if any(p["text"] for p in pages):
            logger.info("[PDF] PyMuPDF per-page OK")
            return pages

        logger.warning("[PDF] PyMuPDF empty → pdfplumber")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF page extraction failed: {e}")

    # --- pdfplumber ---
    try:
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                pages.append({
                    "page": i + 1,
                    "text": (page.extract_text() or "").strip()
                })

        if any(p["text"] for p in pages):
            logger.info("[PDF] pdfplumber per-page OK")
            return pages

        logger.warning("[PDF] pdfplumber empty → PyPDF2")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # --- PyPDF2 ---
    try:
        pages = []
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            pages.append({
                "page": i + 1,
                "text": (page.extract_text() or "").strip()
            })

        if any(p["text"] for p in pages):
            logger.info("[PDF] PyPDF2 per-page OK")
            return pages

        logger.warning("[PDF] PyPDF2 empty → OCR fallback")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # --- OCR fallback ---
    text = await google_ocr_pdf(path)
    if not text.strip():
        return []

    doc = fitz.open(path)
    page_count = len(doc)
    doc.close()

    return split_text_into_pages(text, page_count)

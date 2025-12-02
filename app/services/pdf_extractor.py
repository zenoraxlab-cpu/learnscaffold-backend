import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader
import os
import httpx

from app.utils.logger import logger
from app.config import OCR_SPACE_API_KEY

"""
Unified PDF extraction pipeline:

Order:
1) Detect scanned PDF (no text layer)
2) PyMuPDF
3) pdfplumber
4) PyPDF2
5) OCR.Space fallback (async)

APIs:
- extract_pdf_text(path)  -> str
- extract_pdf_pages(path) -> [{page, text}]
"""


# =====================================================================
# OCR.SPACE REQUEST
# =====================================================================

async def ocr_space_request(path: str) -> str:
    """
    Sends PDF file to OCR.Space API and returns extracted text.
    """
    logger.info("[OCR.Space] Starting OCR request")

    if not OCR_SPACE_API_KEY:
        logger.error("[OCR.Space] Missing API key. Set OCR_SPACE_API_KEY.")
        return ""

    try:
        with open(path, "rb") as f:
            file_bytes = f.read()

        data = {
            "language": "eng,rus",
            "isOverlayRequired": False,
        }

        files = {
            "file": ("input.pdf", file_bytes, "application/pdf")
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.ocr.space/parse/image",
                data=data,
                files=files,
                headers={"apikey": OCR_SPACE_API_KEY}
            )

        if resp.status_code != 200:
            logger.error(f"[OCR.Space] HTTP {resp.status_code}")
            return ""

        js = resp.json()

        if js.get("OCRExitCode") != 1:
            logger.error(f"[OCR.Space] API error: {js.get('ErrorMessage')}")
            return ""

        parsed = js.get("ParsedResults")
        if not parsed:
            logger.error("[OCR.Space] No ParsedResults")
            return ""

        text = parsed[0].get("ParsedText", "")
        logger.info(f"[OCR.Space] OCR returned {len(text)} characters")
        return text

    except Exception as e:
        logger.error(f"[OCR.Space] Exception: {e}")
        return ""


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
        # If PyMuPDF fails, assume scanned to avoid further crashes
        logger.warning("[PDF] detect_scanned_pdf failed → assuming scanned")
        return True


# =====================================================================
# INTERNAL: SPLIT OCR TEXT INTO PAGES
# =====================================================================

def split_text_into_pages(text: str, page_count: int) -> list:
    """
    Splits OCR text into page_count equal segments.
    (OCR.Space does not return per-page data.)
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
# EXTRACT TEXT
# =====================================================================

async def extract_pdf_text(path: str) -> str:
    logger.info(f"[PDF] extract_pdf_text: {path}")

    # --- scanned PDF → OCR immediately ---
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned PDF → OCR.Space fallback")
        return await ocr_space_request(path)

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

        logger.warning("[PDF] PyPDF2 empty → OCR.Space")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # --- OCR fallback ---
    logger.warning("[PDF] Switching to OCR.Space fallback")
    return await ocr_space_request(path)


# =====================================================================
# EXTRACT TEXT PER PAGE
# =====================================================================

async def extract_pdf_pages(path: str) -> list:
    logger.info(f"[PDF] extract_pdf_pages: {path}")

    # --- scanned → OCR immediately ---
    if detect_scanned_pdf(path):
        logger.warning("[PDF] Scanned → OCR.Space page fallback")

        text = await ocr_space_request(path)
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

        logger.warning("[PDF] PyPDF2 empty → OCR.Space")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # --- OCR fallback ---
    text = await ocr_space_request(path)
    if not text.strip():
        return []

    doc = fitz.open(path)
    page_count = len(doc)
    doc.close()

    return split_text_into_pages(text, page_count)

import fitz  # PyMuPDF
import pdfplumber
from PyPDF2 import PdfReader
import subprocess
import tempfile
import os

from app.utils.logger import logger

"""
PDF extraction service with full fallback chain:

1) PyMuPDF
2) pdfplumber
3) PyPDF2
4) OCR (Tesseract)

Two main APIs:
- extract_pdf_text(path)  → full text
- extract_pdf_pages(path) → per-page text array
"""


# ============================================================
# OCR FALLBACK
# ============================================================

def ocr_pdf_to_text(path: str) -> str:
    """
    Convert PDF pages to images and extract text using Tesseract OCR.
    Used when all normal extractors fail.
    """

    try:
        logger.info("[PDF][OCR] Starting OCR fallback...")

        doc = fitz.open(path)
        text_parts = []

        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=200)

            # store temp image
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                image_path = tmp.name
                pix.save(image_path)

            out_path = image_path + ".txt"

            # run Tesseract silently
            subprocess.run(
                ["tesseract", image_path, out_path.replace(".txt", ""), "-l", "eng+rus"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # read OCR output
            if os.path.exists(out_path):
                with open(out_path, "r", encoding="utf-8") as f:
                    text_parts.append(f.read())

            # cleanup
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(out_path):
                os.remove(out_path)

        doc.close()

        full_text = "\n".join(text_parts)
        logger.info(f"[PDF][OCR] OCR completed, length={len(full_text)}")

        return full_text

    except Exception as e:
        logger.error(f"[PDF][OCR] OCR failed: {e}")
        return ""


# ============================================================
# FULL DOCUMENT TEXT EXTRACTION
# ============================================================

def extract_pdf_text(path: str) -> str:
    """
    Extract full text using:
    1) PyMuPDF
    2) pdfplumber
    3) PyPDF2
    4) OCR fallback
    """

    logger.info(f"[PDF] extract_pdf_text(): starting for {path}")

    # ------------ 1) PyMuPDF ------------
    try:
        doc = fitz.open(path)
        text = "\n".join((page.get_text("text") or "") for page in doc)
        doc.close()

        if len(text.strip()) > 20:
            logger.info("[PDF] PyMuPDF text OK")
            return text

        logger.warning("[PDF] PyMuPDF returned too little text → pdfplumber")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF failed: {e}")

    # ------------ 2) pdfplumber ------------
    try:
        temp = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    temp += t + "\n"

        if len(temp.strip()) > 20:
            logger.info("[PDF] pdfplumber text OK")
            return temp

        logger.warning("[PDF] pdfplumber returned too little text → PyPDF2")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # ------------ 3) PyPDF2 ------------
    try:
        temp = ""
        reader = PdfReader(path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                temp += t + "\n"

        if len(temp.strip()) > 20:
            logger.info("[PDF] PyPDF2 text OK")
            return temp

        logger.warning("[PDF] PyPDF2 returned too little text → OCR")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # ------------ 4) OCR fallback ------------
    logger.warning("[PDF] Switching to OCR fallback…")
    text = ocr_pdf_to_text(path)

    if len(text.strip()) > 20:
        logger.info("[PDF] OCR extracted text successfully")
        return text

    logger.error("[PDF] OCR also failed — returning empty text")
    return ""


# ============================================================
# PAGE-BY-PAGE TEXT EXTRACTION
# ============================================================

def extract_pdf_pages(path: str) -> list:
    """
    Returns:
    [
        { "page": 1, "text": "..." },
        ...
    ]

    With OCR fallback if normal extractors fail.
    """

    logger.info(f"[PDF] extract_pdf_pages(): starting for {path}")

    # ------------ 1) PyMuPDF ------------
    try:
        doc = fitz.open(path)
        pages = []

        for i, page in enumerate(doc):
            t = page.get_text("text") or ""
            pages.append({"page": i + 1, "text": t.strip()})

        doc.close()

        if any(p["text"] for p in pages):
            logger.info("[PDF] Page extraction via PyMuPDF OK")
            return pages

        logger.warning("[PDF] PyMuPDF empty pages → pdfplumber")

    except Exception as e:
        logger.warning(f"[PDF] PyMuPDF page extraction failed: {e}")

    # ------------ 2) pdfplumber ------------
    try:
        pages = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                t = page.extract_text() or ""
                pages.append({"page": i + 1, "text": t.strip()})

        if any(p["text"] for p in pages):
            logger.info("[PDF] Page extraction via pdfplumber OK")
            return pages

        logger.warning("[PDF] pdfplumber empty pages → PyPDF2")

    except Exception as e:
        logger.warning(f"[PDF] pdfplumber failed: {e}")

    # ------------ 3) PyPDF2 ------------
    try:
        pages = []
        reader = PdfReader(path)
        for i, page in enumerate(reader.pages):
            t = page.extract_text() or ""
            pages.append({"page": i + 1, "text": t.strip()})

        if any(p["text"] for p in pages):
            logger.info("[PDF] Page extraction via PyPDF2 OK")
            return pages

        logger.warning("[PDF] PyPDF2 empty → OCR fallback")

    except Exception as e:
        logger.warning(f"[PDF] PyPDF2 failed: {e}")

    # ------------ 4) OCR fallback ------------
    logger.warning("[PDF] Using OCR fallback for page-by-page extraction")

    full_text = ocr_pdf_to_text(path)

    if not full_text.strip():
        logger.error("[PDF] OCR also failed — returning empty pages")
        return []

    # Split OCR-output into pseudo-pages evenly
    doc = fitz.open(path)
    pages_count = len(doc)
    doc.close()

    chunk_size = max(1, len(full_text) // pages_count)

    ocr_pages = []
    for i in range(pages_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        ocr_pages.append({
            "page": i + 1,
            "text": full_text[start:end].strip()
        })

    logger.info("[PDF] OCR page fallback returned %d pages", len(ocr_pages))
    return ocr_pages

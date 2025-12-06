from fastapi import APIRouter, HTTPException
from enum import Enum
from typing import Dict
import os
import json

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.services.google_ocr import google_ocr_pdf
from app.config import UPLOAD_DIR

router = APIRouter()


# ---------------------------------------------------------
# TASK STATUS
# ---------------------------------------------------------
class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    EXTRACTING_TEXT = "extracting_text"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    CLASSIFYING = "classifying"
    STRUCTURE = "structure"
    READY = "ready"
    ERROR = "error"


task_status: Dict[str, dict] = {}


def set_status(file_id: str, status: TaskStatus, details: dict = None, msg: str = None):
    task_status[file_id] = {
        "file_id": file_id,
        "status": status.value,
        "details": details,
        "message": msg,
    }
    logger.info(f"[STATUS] {file_id} → {status.value}")


# ---------------------------------------------------------
# ANALYZE
# ---------------------------------------------------------
@router.post("/analyze/")
async def analyze(file_id: str):
    logger.info(f"[ANALYZE] Start → {file_id}")

    set_status(file_id, TaskStatus.ANALYZING)

    try:
        input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        # ---------------------------------------------------------
        # Extract pages
        # ---------------------------------------------------------
        pages = extract_pdf_pages(input_path)
        page_total = len(pages)

        set_status(file_id, TaskStatus.EXTRACTING, {"pages": page_total})

        logger.info(f"[PAGES] Found {page_total} pages")

        # ---------------------------------------------------------
        # OCR OR TEXT
        # ---------------------------------------------------------
        if page_total > 0 and pages[0].get("ocr_needed", False):
            logger.info("[OCR] Using Google OCR")

            full_text = ""
            for idx, page in enumerate(pages):
                part = await google_ocr_pdf(input_path)
                full_text += part + "\n"

                set_status(
                    file_id,
                    TaskStatus.EXTRACTING_TEXT,
                    {"page_current": idx + 1, "page_total": page_total},
                )
        else:
            logger.info("[PDF] Normal text extraction")
            full_text = await extract_pdf_text(input_path)

        logger.info(f"[TEXT] Extracted chars: {len(full_text)}")

        # ---------------------------------------------------------
        # Clean text
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CLEANING)
        cleaned = clean_text(full_text)
        logger.info(f"[CLEAN] Cleaned length = {len(cleaned)}")

        # ---------------------------------------------------------
        # Detect language
        # ---------------------------------------------------------
        from langdetect import detect

        document_language = detect(cleaned[:5000]) if cleaned.strip() else "en"
        logger.info(f"[LANG] → {document_language}")

        # ---------------------------------------------------------
        # Chunk text
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CHUNKING)
        chunks = chunk_text(cleaned)

        # ---------------------------------------------------------
        # Classify
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CLASSIFYING)
        classification = classify_document(chunks)

        # ---------------------------------------------------------
        # Extract structure
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.STRUCTURE)
        structure = extract_structure(cleaned, classification)

        logger.info(f"[STRUCTURE] Units found: {len(structure)}")

        # ---------------------------------------------------------
        # BUILD RESULT JSON
        # ---------------------------------------------------------
        save_path = os.path.join(UPLOAD_DIR, f"{file_id}_analysis.json")

        analysis_data = {
            "file_id": file_id,
            "document_type": classification.get("document_type", ""),
            "main_topics": classification.get("main_topics", []),
            "summary": classification.get("summary", ""),
            "recommended_days": classification.get("recommended_days", 7),
            "structure": structure,
            "document_language": document_language,
            "length_chars": len(cleaned),
            "pages": page_total
        }

        # Save JSON
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)

        set_status(file_id, TaskStatus.READY)
        logger.info("[ANALYZE] DONE")

        # IMPORTANT: frontend expects { analysis: {...} }
        return {"analysis": analysis_data}

    except Exception as e:
        logger.error("[ANALYZE] ERROR")
        logger.exception(e)
        set_status(file_id, TaskStatus.ERROR, msg=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# GET STATUS
# ---------------------------------------------------------
@router.get("/analyze/status/{file_id}")
def get_status(file_id: str):
    return task_status.get(file_id, {"file_id": file_id, "status": "unknown"})


# ---------------------------------------------------------
# LOAD SAVED ANALYSIS
# ---------------------------------------------------------
def load_saved_analysis(file_id: str) -> dict:
    path = os.path.join(UPLOAD_DIR, f"{file_id}_analysis.json")

    if not os.path.exists(path):
        raise FileNotFoundError(f"Analysis not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

from fastapi import APIRouter, HTTPException, Body
from enum import Enum
import os
import json
from typing import Dict

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.services.notifier import send_telegram_alert
from app.config import UPLOAD_DIR

router = APIRouter()


# ---------------------------------------------------------
# TASK STATUS STRUCTURE
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
# MAIN ENDPOINT — /analyze
# ---------------------------------------------------------
@router.post("/analyze")
@router.post("/analyze/")
async def analyze(payload=Body(...)):
    # Унификация входа
    if isinstance(payload, dict) and "file_id" in payload:
        file_id = payload["file_id"]
    else:
        file_id = str(payload)

    logger.info(f"[ANALYZE] Start → file {file_id}")
    set_status(file_id, TaskStatus.ANALYZING)

    try:
        input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        # ---------------------------------------------------------
        # Extract pages metadata
        # ---------------------------------------------------------
        pages = extract_pdf_pages(input_path)
        page_total = len(pages)
        set_status(file_id, TaskStatus.EXTRACTING, {"pages": page_total})

        # ---------------------------------------------------------
        # Extract raw text
        # ---------------------------------------------------------
        full_text = await extract_pdf_text(input_path)
        logger.info(f"[TEXT] Extracted: {len(full_text)} chars")

        set_status(file_id, TaskStatus.CLEANING)
        cleaned = clean_text(full_text)

        # ---------------------------------------------------------
        # Detect language
        # ---------------------------------------------------------
        try:
            from langdetect import detect
            document_language = detect(cleaned[:5000]) if cleaned.strip() else "en"
        except:
            document_language = "en"

        logger.info(f"[LANG] → {document_language}")

        # ---------------------------------------------------------
        # Chunking
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CHUNKING)
        chunks = chunk_text(cleaned)

        # ---------------------------------------------------------
        # Classification
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CLASSIFYING)
        classification = classify_document(chunks)

        # ---------------------------------------------------------
        # STRUCTURE EXTRACTION (PDF → LLM fallback)
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.STRUCTURE)

        # 1) Try PDF headings
        try:
            structure = extract_structure(input_path) or []
            logger.info(f"[STRUCTURE] Extracted PDF headings: {len(structure)}")
        except Exception as se:
            logger.error(f"[STRUCTURE] Failed: {se}")
            structure = []

        # 2) If empty — use LLM fallback
        if not structure:
            logger.warning("[STRUCTURE] No PDF headings → switching to LLM fallback")
            try:
                from app.services.llm_structure import extract_structure_llm
                structure = extract_structure_llm(cleaned[:200000], document_language) or []
                logger.warning(f"[LLM_STRUCTURE] Returned blocks: {len(structure)}")
            except Exception as le:
                logger.error(f"[LLM_STRUCTURE] Failed: {le}")
                structure = []

        # 3) Final check
        if not structure:
            logger.error("[STRUCTURE] Final failure: no structure extracted")

        # ---------------------------------------------------------
        # SAVE ANALYSIS
        # ---------------------------------------------------------
        analysis_data = {
            "file_id": file_id,
            "document_type": classification.get("document_type", "text"),
            "main_topics": classification.get("main_topics", []),
            "summary": classification.get("summary", ""),
            "recommended_days": classification.get("recommended_days", 7),
            "structure": structure,
            "document_language": document_language,
            "length_chars": len(cleaned),
            "pages": page_total,
        }

        save_path = os.path.join(UPLOAD_DIR, f"{file_id}_analysis.json")
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)

        set_status(file_id, TaskStatus.READY)
        logger.info("[ANALYZE] Completed OK")

        return {"analysis": analysis_data}

    # ---------------------------------------------------------
    # ERROR HANDLER
    # ---------------------------------------------------------
    except Exception as e:
        logger.error("=== ANALYZE FAILED ===")
        logger.error(f"FILE → {file_id}")
        logger.error(f"ERROR → {type(e).__name__}: {str(e)}")
        logger.exception(e)

        set_status(file_id, TaskStatus.ERROR, msg=str(e))

        try:
            send_telegram_alert(
                f"❗ ANALYZE FAILED\n"
                f"File ID: {file_id}\n"
                f"Ошибка: {str(e)}\n"
                f"Файл требует ручной обработки."
            )
        except:
            pass

        return {
            "status": "delayed",
            "file_id": file_id,
            "message": "Your file requires extended processing. We will send results to your email when ready."
        }


# ---------------------------------------------------------
# GET STATUS
# ---------------------------------------------------------
@router.get("/analyze/status/{file_id}")
@router.get("/analyze/status/{file_id}/")
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

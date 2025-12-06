from fastapi import APIRouter, HTTPException
import os
from typing import Optional, Dict, Any
from enum import Enum

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.google_ocr import google_ocr_pdf
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.config import UPLOAD_DIR

router = APIRouter()

# ======================================================================
# TASK STATUS TRACKING
# ======================================================================

class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    EXTRACTING_TEXT = "extracting_text"
    CHUNKING = "chunking"
    CLASSIFYING = "classifying"
    STRUCTURE = "structure"
    READY = "ready"
    ERROR = "error"


task_status: Dict[str, str] = {}
task_msg: Dict[str, str] = {}
task_status_details: Dict[str, Dict[str, Any]] = {}


def set_status(file_id: str, status: TaskStatus, msg: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    task_status[file_id] = status
    if msg:
        task_msg[file_id] = msg
    if details:
        task_status_details[file_id] = details

    logger.info(f"[STATUS] {file_id} → {status} {msg if msg else ''}")


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    return {
        "file_id": file_id,
        "status": task_status.get(file_id),
        "message": task_msg.get(file_id),
        "details": task_status_details.get(file_id),
    }


# ======================================================================
# ANALYSIS PIPELINE
# ======================================================================

@router.post("/")
async def analyze(payload: dict):
    file_id = payload.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id")

    input_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"[ANALYZE] Start file_id={file_id}")
    set_status(file_id, TaskStatus.ANALYZING)

    try:
        # ---------------------------------------------------------
        # Extract Pages
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.EXTRACTING)
        logger.info(f"[PDF] extract_pdf_pages: {input_path}")

        pages = extract_pdf_pages(input_path)
        page_total = len(pages)
        logger.info(f"[PDF] Pages extracted → {page_total}")

        # ---------------------------------------------------------
        # Text Extraction
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.EXTRACTING_TEXT)

               # OCR MODE
        if page_total > 0 and pages[0].get("ocr_needed", False):
            logger.info("[PDF] Using GOOGLE OCR mode")

            full_text = ""
            ocr_total = len(pages)

            for idx, p in enumerate(pages):
                text = await google_ocr_pdf(input_path)
                full_text += text + "\n"

                set_status(
                    file_id,
                    TaskStatus.EXTRACTING_TEXT,
                    details={"page_current": idx + 1, "page_total": ocr_total}
                )

        else:
            logger.info("[PDF] Normal text extraction")
            full_text = await extract_pdf_text(input_path)

        logger.info(f"[ANALYZE] extract_pdf_text OK ({len(full_text)} chars)")

        # ---------------------------------------------------------
        # Clean text
        # ---------------------------------------------------------
        logger.info("Text cleaning started")
        cleaned = clean_text(full_text)
        logger.info(f"Text cleaning finished, length={len(cleaned)}")

        # ---------------------------------------------------------
        # Detect language
        # ---------------------------------------------------------
        logger.info("Detecting language…")
        from langdetect import detect
        document_language = detect(cleaned[:5000]) if cleaned.strip() else "en"
        logger.info(f"[ANALYZE] Language → {document_language}")

        # ---------------------------------------------------------
        # Chunking
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CHUNKING)
        chunks = chunk_text(cleaned)
        logger.info(f"[ANALYZE] chunking OK → {len(chunks)} chunks")

        # ---------------------------------------------------------
        # Classification
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.CLASSIFYING)
        classification = classify_document(chunks)
        logger.info("[CLASSIFIER] Completed")

        # ---------------------------------------------------------
        # Structure detection
        # ---------------------------------------------------------
        set_status(file_id, TaskStatus.STRUCTURE)
        structure = extract_structure(cleaned)
        logger.info(f"[STRUCTURE] Units found: {len(structure)}")

        try:
        # ---------------------------------------------------------
        # Save analysis JSON
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

        import json
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(analysis_data, f, ensure_ascii=False, indent=2)

        set_status(file_id, TaskStatus.READY)
        logger.info("[ANALYZE] DONE")

        # 🎯 Ключевой момент:
        # Frontend ждёт обёртку {analysis: {...}}
        return {"analysis": analysis_data}

    except Exception as e:
        logger.error("[ANALYZE] ERROR")
        logger.exception(e)
        set_status(file_id, TaskStatus.ERROR, msg=str(e))
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------------------------------------
# Load saved analysis JSON
# ---------------------------------------------------------
def load_saved_analysis(file_id: str) -> dict:
    import json
    import os
    from app.config import UPLOAD_DIR

    path = os.path.join(UPLOAD_DIR, f"{file_id}_analysis.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Analysis file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

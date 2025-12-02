from fastapi import APIRouter, HTTPException
import os
from typing import Optional, Dict
from enum import Enum

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.config import UPLOAD_DIR

router = APIRouter()

# -----------------------------------------------------------
# GLOBAL TASK STATUS STORAGE
# -----------------------------------------------------------

class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    CLASSIFYING = "classifying"
    STRUCTURE = "structure"
    READY = "ready"
    ERROR = "error"

task_status: Dict[str, str] = {}


def set_status(file_id: str, status: TaskStatus):
    task_status[file_id] = status
    logger.info(f"[STATUS] {file_id} → {status}")


# -----------------------------------------------------------
# ANALYZE ENDPOINT
# -----------------------------------------------------------

@router.post("/")
async def analyze_document(file_id: str):
    """
    Improved document analysis pipeline with status tracking.
    """

    logger.info(f"[ANALYZE] Starting for file_id={file_id}")

    # Mark as started
    set_status(file_id, TaskStatus.ANALYZING)

    # -----------------------------------------------------------
    # 1) Locate file
    # -----------------------------------------------------------
    file_path: Optional[str] = None

    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path:
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"[ANALYZE] File located: {file_path}")

    # -----------------------------------------------------------
    # 2) Extract pages
    # -----------------------------------------------------------
    try:
        set_status(file_id, TaskStatus.EXTRACTING)
        pages = extract_pdf_pages(file_path)
        logger.info(f"[ANALYZE] Extracted {len(pages)} pages")
    except Exception as e:
        logger.exception(f"[ANALYZE] Page extraction failed: {e}")
        pages = []

    # -----------------------------------------------------------
    # 3) Extract main text
    # -----------------------------------------------------------
    raw_text = extract_pdf_text(file_path)

    if not raw_text or not raw_text.strip():
        logger.warning("[ANALYZE] Text empty, fallback to page text")

        if pages:
            joined = [
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in pages
            ]
            raw_text = "\n\n".join(joined)

    if not raw_text.strip():
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Failed to extract text")

    # -----------------------------------------------------------
    # 4) Clean text
    # -----------------------------------------------------------
    cleaned = clean_text(raw_text)
    if not cleaned.strip():
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(
            status_code=500,
            detail="Text cleaning produced empty output"
        )

    # -----------------------------------------------------------
    # 5) Chunk text
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CHUNKING)
    chunks = chunk_text(cleaned, max_chars=2000, overlap=200)

    if not chunks:
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Chunking failed")

    # -----------------------------------------------------------
    # 6) LLM classification
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CLASSIFYING)
    analysis = classify_document(chunks[0])
    logger.info(f"[ANALYZE] Classification: {analysis}")

    # -----------------------------------------------------------
    # 7) Extract structure
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.STRUCTURE)
    structure = extract_structure(file_path) or []
    logger.info(f"[ANALYZE] Structure units: {len(structure)}")

    # -----------------------------------------------------------
    # 8) Basic analytics
    # -----------------------------------------------------------
    total_len = len(cleaned)
    chunk_count = len(chunks)
    preview = chunks[0][:1000]

    # Done
    set_status(file_id, TaskStatus.READY)

    logger.info(
        f"[ANALYZE] Completed: len={total_len}, chunks={chunk_count}, pages={len(pages)}"
    )

    return {
        "status": "ok",
        "file_id": file_id,
        "total_length": total_len,
        "chunks_count": chunk_count,
        "pages": len(pages),
        "first_chunk_preview": preview,
        "analysis": analysis,
        "structure": structure,
    }


# -----------------------------------------------------------
# STATUS ENDPOINT FOR FRONTEND
# -----------------------------------------------------------

@router.get("/status/{file_id}")
async def get_status(file_id: str):
    """
    Returns current status for progress-bar on frontend.
    """
    return {"file_id": file_id, "status": task_status.get(file_id, "unknown")}

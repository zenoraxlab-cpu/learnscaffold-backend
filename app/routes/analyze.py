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


def set_status(file_id: str, status: TaskStatus):
    task_status[file_id] = status
    logger.info(f"[STATUS] {file_id} → {status}")


# ======================================================================
# MAIN ANALYSIS ENDPOINT
# ======================================================================

@router.post("/")
async def analyze_document(file_id: str):
    logger.info(f"[ANALYZE] Start file_id={file_id}")
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

    logger.info(f"[ANALYZE] File located → {file_path}")

    # -----------------------------------------------------------
    # 2) Extract pages (per-page text, async)
    # -----------------------------------------------------------
    try:
        set_status(file_id, TaskStatus.EXTRACTING)
        pages = await extract_pdf_pages(file_path)
        logger.info(f"[ANALYZE] extract_pdf_pages OK: {len(pages)} pages")
    except Exception as e:
        logger.exception(f"[ANALYZE] extract_pdf_pages failed: {e}")
        pages = []

    # -----------------------------------------------------------
    # 3) Extract full text (async)
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.EXTRACTING_TEXT)

    try:
        raw_text = await extract_pdf_text(file_path)
        logger.info(f"[ANALYZE] extract_pdf_text OK ({len(raw_text)} chars)")
    except Exception as e:
        logger.error(f"[ANALYZE] extract_pdf_text crashed: {e}")
        raw_text = ""

    # Fallback: join per-page text
    if not raw_text.strip():
        logger.warning("[ANALYZE] Text empty → fallback to pages[]")
        if pages:
            raw_text = "\n\n".join([p.get("text", "") for p in pages])

    if not raw_text.strip():
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Failed to extract text from document")

    # -----------------------------------------------------------
    # 4) Clean text
    # -----------------------------------------------------------
    cleaned = clean_text(raw_text)
    if not cleaned.strip():
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Text cleaning failed")

    # -----------------------------------------------------------
    # 5) Chunk text
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CHUNKING)

    chunks = chunk_text(cleaned, max_chars=2000, overlap=200)
    if not chunks:
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Chunking failed")

    # -----------------------------------------------------------
    # 6) Document classification
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CLASSIFYING)

    try:
        analysis = classify_document(chunks[0])
    except Exception as e:
        logger.error(f"[ANALYZE] classify_document failed: {e}")
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Document classification failed")

    logger.info("[ANALYZE] Classification OK")

    # -----------------------------------------------------------
    # 7) Extract structure (chapters)
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.STRUCTURE)

    try:
        structure = extract_structure(file_path) or []
        logger.info(f"[ANALYZE] Structure extracted: {len(structure)} units")
    except Exception as e:
        logger.error(f"[ANALYZE] Structure extractor failed: {e}")
        structure = []

    # -----------------------------------------------------------
    # 8) Final response
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.READY)

    logger.info(
        f"[ANALYZE] DONE → len={len(cleaned)}, chunks={len(chunks)}, pages={len(pages)}"
    )

    return {
        "status": "ok",
        "file_id": file_id,
        "total_length": len(cleaned),
        "chunks_count": len(chunks),
        "pages": len(pages),
        "first_chunk_preview": chunks[0][:1000],
        "analysis": analysis,
        "structure": structure,
    }


# ======================================================================
# STATUS ENDPOINT (frontend polling)
# ======================================================================

@router.get("/status/{file_id}")
async def get_status(file_id: str):
    return {"file_id": file_id, "status": task_status.get(file_id, "unknown")}

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from typing import Optional, Dict
from enum import Enum

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.services.language import detect_language
from app.services.notifier import notify_admin
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
# REQUEST MODEL
# ======================================================================

class AnalyzeRequest(BaseModel):
    file_id: str


# ======================================================================
# MAIN ANALYSIS ENDPOINT
# ======================================================================

@router.post("/")
async def analyze_document(payload: AnalyzeRequest):
    file_id = payload.file_id

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
        await notify_admin(f"❌ File not found during analysis\nfile_id={file_id}")
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"[ANALYZE] File located → {file_path}")

    # -----------------------------------------------------------
    # 2) Extract pages
    # -----------------------------------------------------------
    try:
        set_status(file_id, TaskStatus.EXTRACTING)
        pages = await extract_pdf_pages(file_path)
        logger.info(f"[ANALYZE] extract_pdf_pages OK: {len(pages)} pages")
    except Exception as e:
        logger.exception(f"[ANALYZE] extract_pdf_pages failed: {e}")
        pages = []
        await notify_admin(
            f"❌ ANALYZE ERROR (extract_pdf_pages)\nfile_id={file_id}\n{e}"
        )

    # -----------------------------------------------------------
    # 3) Extract full text
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.EXTRACTING_TEXT)

    try:
        raw_text = await extract_pdf_text(file_path)
        logger.info(f"[ANALYZE] extract_pdf_text OK ({len(raw_text)} chars)")
    except Exception as e:
        logger.error(f"[ANALYZE] extract_pdf_text crashed: {e}")
        raw_text = ""
        await notify_admin(
            f"❌ ANALYZE ERROR (extract_pdf_text)\nfile_id={file_id}\n{e}"
        )

    if not raw_text.strip() and pages:
        raw_text = "\n\n".join([p.get("text", "") for p in pages])

    if not raw_text.strip():
        await notify_admin(
            f"❌ ANALYZE ERROR: No text extracted\nfile_id={file_id}"
        )
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Failed to extract text")

    # -----------------------------------------------------------
    # 4) Clean text
    # -----------------------------------------------------------
    cleaned = clean_text(raw_text)

    if not cleaned.strip():
        await notify_admin(
            f"❌ ANALYZE ERROR (clean_text returned empty)\nfile_id={file_id}"
        )
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Text cleaning failed")

    # -----------------------------------------------------------
    # 4.1 Detect language
    # -----------------------------------------------------------
    try:
        language = detect_language(cleaned)
        logger.info(f"[ANALYZE] Language → {language}")
    except Exception as e:
        logger.error(f"[ANALYZE] Language detection failed: {e}")
        language = "en"

    # -----------------------------------------------------------
    # 5) Chunk text
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CHUNKING)

    chunks = chunk_text(cleaned, max_chars=2000, overlap=200)
    if not chunks:
        await notify_admin(
            f"❌ ANALYZE ERROR (chunk_text returned 0)\nfile_id={file_id}"
        )
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Chunking failed")

    # -----------------------------------------------------------
    # 6) Classification
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.CLASSIFYING)

    try:
        analysis = classify_document(chunks[0])
    except Exception as e:
        await notify_admin(
            f"❌ ANALYZE ERROR (classify_document)\nfile_id={file_id}\n{e}"
        )
        set_status(file_id, TaskStatus.ERROR)
        raise HTTPException(status_code=500, detail="Classification failed")

    # -----------------------------------------------------------
    # 7) Structure extraction
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.STRUCTURE)

    try:
        structure = extract_structure(file_path) or []
    except Exception as e:
        logger.error(f"[ANALYZE] Structure extractor failed: {e}")
        structure = []
        await notify_admin(
            f"⚠️ ANALYZE WARNING: structure extraction failed\nfile_id={file_id}\n{e}"
        )

    # -----------------------------------------------------------
    # 8) Done
    # -----------------------------------------------------------
    set_status(file_id, TaskStatus.READY)

    logger.info(
        f"[ANALYZE] DONE → len={len(cleaned)}, chunks={len(chunks)}, "
        f"pages={len(pages)}, lang={language}"
    )

    return {
        "status": "ok",
        "file_id": file_id,
        "total_length": len(cleaned),
        "chunks_count": len(chunks),
        "pages": len(pages),
        "analysis": analysis,
        "structure": structure,
        "language": language,
    }


@router.get("/status/{file_id}")
async def get_status(file_id: str):
    return {"file_id": file_id, "status": task_status.get(file_id, "unknown")}

from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from enum import Enum
import os
import json
import uuid
from typing import Dict
from datetime import datetime

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.pdf_text import extract_clean_text
from app.services.structure_extractor import extract_structure_from_text
from app.config import UPLOAD_DIR

router = APIRouter()

# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------
class TaskStatus(str, Enum):
    RUNNING = "running"
    READY = "ready"
    ERROR = "error"

task_status: Dict[str, dict] = {}

def now():
    return datetime.utcnow().isoformat()

# ---------------------------------------------------------
# INIT — анализ PDF + summary для фронта
# ---------------------------------------------------------
@router.post("/analyze/init")
async def analyze_init(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files supported")

    task_id = str(uuid.uuid4())
    filename = f"{task_id}.pdf"
    pdf_path = os.path.join(UPLOAD_DIR, filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    # --- PDF ---
    pages = extract_pdf_pages(pdf_path)
    full_text = await extract_pdf_text(pdf_path)
    cleaned = clean_text(full_text)

    # --- CLASSIFICATION ---
    try:
        classification = classify_document(cleaned)

        days = classification.get("recommended_days", 10)
        document_type = classification.get("document_type", "Document")
        summary = classification.get("summary", "")
        main_topics = classification.get("main_topics", [])

    except Exception as e:
        logger.warning(f"[CLASSIFIER] Failed: {e}")
        days = 10
        document_type = "Document"
        summary = ""
        main_topics = []

    # --- SAVE INIT ---
    with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "original_file": filename,
                "document_type": document_type,
                "summary": summary,
                "main_topics": main_topics,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    task_status[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.READY,
        "stage": "init",
        "progress": 100,
        "updated_at": now(),
    }

    # --- RESPONSE FOR FRONT ---
    return {
        "task_id": task_id,
        "pages": len(pages),
        "document_type": document_type,
        "summary": summary,
        "main_topics": main_topics[:5],
        "suggested_plan": {
            "days": days,
            "hours_per_day": 3,
        },
    }

# ---------------------------------------------------------
# GENERATE (пошаговый fake-progress, фронту всё равно)
# ---------------------------------------------------------
@router.post("/analyze/generate")
def generate(task_id: str = Body(..., embed=True)):
    return _advance_task(task_id)

@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    return _advance_task(task_id)

# ---------------------------------------------------------
# CORE LOGIC
# ---------------------------------------------------------
def _advance_task(task_id: str):
    state = task_status.get(task_id)

    if not state:
        raise HTTPException(404, detail="Task not found")

    stage = state.get("stage")

    # ---------- START ----------
    if stage == "init":
        state.update({
            "status": TaskStatus.RUNNING,
            "stage": "extracting",
            "progress": 10,
            "updated_at": now(),
        })
        return state

    # ---------- STEP 1 ----------
    if stage == "extracting":
        with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json"), encoding="utf-8") as f:
            init = json.load(f)

        pdf_path = os.path.join(UPLOAD_DIR, init["original_file"])
        text = extract_clean_text(pdf_path)

        with open(os.path.join(UPLOAD_DIR, f"{task_id}_text.json"), "w", encoding="utf-8") as f:
            json.dump(text, f, ensure_ascii=False)

        state.update({
            "stage": "structure",
            "progress": 60,
            "updated_at": now(),
        })
        return state

    # ---------- STEP 2 ----------
    if stage == "structure":
        with open(os.path.join(UPLOAD_DIR, f"{task_id}_text.json"), encoding="utf-8") as f:
            text = json.load(f)

        structure = extract_structure_from_text(text)

        with open(os.path.join(UPLOAD_DIR, f"{task_id}_final.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "task_id": task_id,
                    "structure": structure,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        state.update({
            "status": TaskStatus.READY,
            "stage": "done",
            "progress": 100,
            "updated_at": now(),
        })
        return state

    # ---------- DONE ----------
    return state

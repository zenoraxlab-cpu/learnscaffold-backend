from fastapi import APIRouter, UploadFile, File, HTTPException, Body, BackgroundTasks
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
from app.services.notifier import send_telegram_alert
from app.services.structure_extractor import extract_structure
from app.services.pdf_text import extract_clean_text
from app.services.llm_structure import extract_structure_llm
from app.config import UPLOAD_DIR

router = APIRouter()

# ---------------------------------------------------------
# STATUS ENUM
# ---------------------------------------------------------
class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    STRUCTURE = "structure"
    READY = "ready"
    ERROR = "error"

# ---------------------------------------------------------
# IN-MEMORY STATUS STORAGE
# ---------------------------------------------------------
task_status: Dict[str, dict] = {}

def set_status(
    task_id: str,
    status: TaskStatus,
    progress: int = 0,
    eta_min: int | None = None,
    msg: str | None = None,
):
    task_status[task_id] = {
        "task_id": task_id,
        "status": status.value,
        "progress": progress,
        "eta_min": eta_min,
        "message": msg,
        "updated_at": datetime.utcnow().isoformat(),
    }
    logger.info(f"[STATUS] {task_id} → {status.value} ({progress}%)")

# ---------------------------------------------------------
# BACKGROUND GENERATION (NO CELERY)
# ---------------------------------------------------------
def run_full_generation_sync(task_id: str, days: int, hours_per_day: int):
    try:
        set_status(task_id, TaskStatus.EXTRACTING, progress=10)

        init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
        with open(init_path, "r", encoding="utf-8") as f:
            init_data = json.load(f)

        pdf_path = os.path.join(UPLOAD_DIR, init_data["original_file"])

        text = extract_clean_text(pdf_path)
        set_status(task_id, TaskStatus.CLEANING, progress=40)

        try:
            structure = extract_structure_llm(text)
        except Exception:
            structure = extract_structure(text)

        set_status(task_id, TaskStatus.STRUCTURE, progress=70)

        result_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "task_id": task_id,
                    "days": days,
                    "hours_per_day": hours_per_day,
                    "structure": structure,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        set_status(task_id, TaskStatus.READY, progress=100)

    except Exception as e:
        logger.error(f"[GENERATION FAILED] {task_id}: {e}")
        set_status(task_id, TaskStatus.ERROR, msg=str(e))
        send_telegram_alert(f"GENERATION FAILED\nTask: {task_id}\nError: {e}")

# ---------------------------------------------------------
# STAGE 1 — INIT
# ---------------------------------------------------------
@router.post("/analyze/init")
async def analyze_init(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, detail="Only PDF files are supported")

    task_id = str(uuid.uuid4())
    filename = f"{task_id}.pdf"
    input_path = os.path.join(UPLOAD_DIR, filename)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(input_path, "wb") as f:
        f.write(await file.read())

    try:
        pages = extract_pdf_pages(input_path)
        full_text = await extract_pdf_text(input_path)
        cleaned = clean_text(full_text)

        try:
            from langdetect import detect
            document_language = detect(cleaned[:5000]) if cleaned.strip() else "en"
        except Exception:
            document_language = "en"

        try:
            classification = classify_document(cleaned)
            recommended_days = classification.get("recommended_days", 10)
        except Exception:
            recommended_days = 10

        init_data = {
            "original_file": filename,
            "pages": len(pages),
            "length_chars": len(cleaned),
            "document_language": document_language,
        }

        with open(
            os.path.join(UPLOAD_DIR, f"{task_id}_init.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(init_data, f)

        set_status(task_id, TaskStatus.READY, progress=100)

        return {
            "task_id": task_id,
            "pages": len(pages),
            "detected_language": document_language.upper(),
            "suggested_plan": {
                "days": recommended_days,
                "hours_per_day": 3,
            },
        }

    except Exception as e:
        logger.error(f"[INIT FAILED] {task_id}: {e}")
        set_status(task_id, TaskStatus.ERROR, msg=str(e))
        raise HTTPException(500, detail="Initial analysis failed")

# ---------------------------------------------------------
# STAGE 2 — GENERATE (BACKGROUND)
# ---------------------------------------------------------
@router.post("/analyze/generate")
async def start_generate(
    background_tasks: BackgroundTasks,
    task_id: str = Body(..., embed=True),
    days: int = Body(10),
    hours_per_day: int = Body(3),
):
    init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
    if not os.path.exists(init_path):
        raise HTTPException(404, detail="Task not found")

    set_status(task_id, TaskStatus.ANALYZING, progress=0, eta_min=days * 2)

    background_tasks.add_task(
        run_full_generation_sync,
        task_id,
        days,
        hours_per_day,
    )

    return {"task_id": task_id, "status": "started"}

# ---------------------------------------------------------
# STATUS
# ---------------------------------------------------------
@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    status = task_status.get(task_id)
    if not status:
        raise HTTPException(404, detail="Task not found")
    return status

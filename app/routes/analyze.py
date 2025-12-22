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
from app.services.structure_extractor import extract_structure_from_text
from app.services.pdf_text import extract_clean_text
from app.config import UPLOAD_DIR

router = APIRouter()

# ---------------------------------------------------------
# STATUS ENUM
# ---------------------------------------------------------
class TaskStatus(str, Enum):
    READY = "ready"
    ERROR = "error"

# ---------------------------------------------------------
# IN-MEMORY STATUS
# ---------------------------------------------------------
task_status: Dict[str, dict] = {}

def set_status(task_id: str, status: TaskStatus, progress: int = 0):
    task_status[task_id] = {
        "task_id": task_id,
        "status": status.value,
        "progress": progress,
        "updated_at": datetime.utcnow().isoformat(),
    }
    logger.info(f"[STATUS] {task_id} → {status.value} ({progress}%)")

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
            classification = classify_document(cleaned)
            recommended_days = classification.get("recommended_days", 10)
        except Exception:
            recommended_days = 10

        init_data = {
            "original_file": filename,
            "pages": len(pages),
            "length_chars": len(cleaned),
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
            "suggested_plan": {
                "days": recommended_days,
                "hours_per_day": 3,
            },
        }

    except Exception as e:
        logger.error(f"[INIT FAILED] {task_id}: {e}")
        set_status(task_id, TaskStatus.ERROR)
        raise HTTPException(500, detail="Initial analysis failed")

# ---------------------------------------------------------
# STAGE 2 — GENERATE (SYNC, FAST, STABLE)
# ---------------------------------------------------------
@router.post("/analyze/generate")
def generate(
    task_id: str = Body(..., embed=True),
    days: int = Body(10),
    hours_per_day: int = Body(3),
):
    init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
    if not os.path.exists(init_path):
        raise HTTPException(404, detail="Task not found")

    try:
        with open(init_path, "r", encoding="utf-8") as f:
            init_data = json.load(f)

        pdf_path = os.path.join(UPLOAD_DIR, init_data["original_file"])

        # 🔴 ВСЯ РАБОТА ЗДЕСЬ — БЫСТРАЯ
        text_by_page = extract_clean_text(pdf_path)
        structure = extract_structure_from_text(text_by_page)

        result = {
            "task_id": task_id,
            "days": days,
            "hours_per_day": hours_per_day,
            "structure": structure,
        }

        result_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    except Exception as e:
        logger.error(f"[GENERATE FAILED] {task_id}: {e}")
        raise HTTPException(500, detail="Generation failed")

# ---------------------------------------------------------
# STATUS (OPTIONAL)
# ---------------------------------------------------------
@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    status = task_status.get(task_id)
    if not status:
        raise HTTPException(404, detail="Task not found")
    return status

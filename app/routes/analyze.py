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
# INIT
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

    pages = extract_pdf_pages(pdf_path)
    full_text = await extract_pdf_text(pdf_path)
    cleaned = clean_text(full_text)

    try:
        classification = classify_document(cleaned)
        days = classification.get("recommended_days", 10)
    except Exception:
        days = 10

    with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json"), "w") as f:
        json.dump({
            "original_file": filename
        }, f)

    task_status[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.READY,
        "stage": "init",
        "progress": 100,
        "updated_at": now(),
    }

    return {
        "task_id": task_id,
        "pages": len(pages),
        "suggested_plan": {
            "days": days,
            "hours_per_day": 3,
        },
    }

# ---------------------------------------------------------
# GENERATE (START)
# ---------------------------------------------------------
@router.post("/analyze/generate")
def generate(task_id: str = Body(..., embed=True)):
    init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
    if not os.path.exists(init_path):
        raise HTTPException(404, detail="Task not found")

    task_status[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.RUNNING,
        "stage": "extracting",
        "progress": 10,
        "updated_at": now(),
    }

    return {"task_id": task_id, "status": "started"}

# ---------------------------------------------------------
# STATUS + WORK
# ---------------------------------------------------------
@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    state = task_status.get(task_id)
    if not state:
        raise HTTPException(404, detail="Task not found")

    stage = state["stage"]

    # -------- STEP 1: TEXT --------
    if stage == "extracting":
        with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json")) as f:
            init = json.load(f)

        pdf_path = os.path.join(UPLOAD_DIR, init["original_file"])
        text = extract_clean_text(pdf_path)

        with open(os.path.join(UPLOAD_DIR, f"{task_id}_text.json"), "w") as f:
            json.dump(text, f)

        state.update({
            "stage": "structure",
            "progress": 50,
            "updated_at": now(),
        })
        return state

    # -------- STEP 2: STRUCTURE --------
    if stage == "structure":
        with open(os.path.join(UPLOAD_DIR, f"{task_id}_text.json")) as f:
            text = json.load(f)

        structure = extract_structure_from_text(text)

        with open(os.path.join(UPLOAD_DIR, f"{task_id}_final.json"), "w") as f:
            json.dump({
                "task_id": task_id,
                "structure": structure,
            }, f, ensure_ascii=False, indent=2)

        state.update({
            "status": TaskStatus.READY,
            "stage": "done",
            "progress": 100,
            "updated_at": now(),
        })
        return state

    return state

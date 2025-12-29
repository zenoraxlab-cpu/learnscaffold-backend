from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from enum import Enum
import os
import json
import uuid
from typing import Dict
from datetime import datetime

from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.pdf_text import extract_clean_text
from app.config import UPLOAD_DIR

# NEW — semantic + LLM
from app.services.semantic_sections import extract_semantic_sections
from app.services.llm_section_analyzer import analyze_section_with_llm

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
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    pdf_path = os.path.join(UPLOAD_DIR, f"{task_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    pages = extract_pdf_pages(pdf_path)
    full_text = await extract_pdf_text(pdf_path)
    cleaned = clean_text(full_text)

    try:
        classification = classify_document(cleaned)
        days = classification.get("recommended_days", 10)
        document_type = classification.get("document_type", "Document")
        summary = classification.get("summary", "")
        main_topics = classification.get("main_topics", [])
    except Exception:
        days = 10
        document_type = "Document"
        summary = ""
        main_topics = []

    with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "original_file": f"{task_id}.pdf",
                "days": days,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    task_status[task_id] = {
        "task_id": task_id,
        "status": TaskStatus.READY,
        "stage": "init",
        "progress": 0,
        "updated_at": now(),
    }

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
# GENERATE
# ---------------------------------------------------------
@router.post("/analyze/generate")
def generate(payload: dict = Body(...)):
    task_id = payload.get("task_id")
    if not task_id:
        raise HTTPException(422, detail="task_id required")
    return _advance_task(task_id)

@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    return _advance_task(task_id)

# ---------------------------------------------------------
# RESULT
# ---------------------------------------------------------
@router.get("/analyze/result/{task_id}")
def get_analyze_result(task_id: str):
    final_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.json")

    if not os.path.exists(final_path):
        raise HTTPException(status_code=404, detail="Result not ready")

    with open(final_path, encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------
# CORE FLOW
# ---------------------------------------------------------
def _advance_task(task_id: str):
    state = task_status.get(task_id)
    if not state:
        raise HTTPException(404, detail="Task not found")

    stage = state["stage"]

    # INIT → EXTRACTING
    if stage == "init":
        state.update(
            status=TaskStatus.RUNNING,
            stage="extracting",
            progress=20,
            updated_at=now(),
        )
        return state

    # EXTRACTING → AI (NEW LOGIC)
    if stage == "extracting":
        with open(os.path.join(UPLOAD_DIR, f"{task_id}_init.json"), encoding="utf-8") as f:
            init = json.load(f)

        pdf_path = os.path.join(UPLOAD_DIR, init["original_file"])
        text = extract_clean_text(pdf_path)

        # 1️⃣ semantic sections
        raw_sections = extract_semantic_sections(text)

        sections = []
        for idx, sec in enumerate(raw_sections, start=1):
            analysis = analyze_section_with_llm(
                title=sec["title"],
                text=sec["text"][:1500],  # safety limit
            )

            sections.append(
                {
                    "section_id": f"s{idx}",
                    "title": sec["title"],
                    "analysis": analysis,
                }
            )

        ai_plan_v2 = {
            "meta": {
                "audience": "student_self_learning",
                "language": "en",
            },
            "sections": sections,
        }

        final = {
            "task_id": task_id,
            "ai_plan": ai_plan_v2,
        }

        with open(os.path.join(UPLOAD_DIR, f"{task_id}_final.json"), "w", encoding="utf-8") as f:
            json.dump(final, f, ensure_ascii=False, indent=2)

        state.update(
            status=TaskStatus.READY,
            stage="done",
            progress=100,
            updated_at=now(),
        )
        return state

    return state

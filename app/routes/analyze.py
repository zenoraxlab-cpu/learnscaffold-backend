# app/routes/analyze.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Body, BackgroundTasks
from enum import Enum
import os
import json
import uuid
from typing import Dict, Optional
from datetime import datetime

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.notifier import send_telegram_alert
from app.services.structure_extractor import extract_structure_from_text, extract_structure
from app.services.pdf_text import extract_clean_text
from app.services.llm_structure import extract_structure_llm  # если есть
from app.config import UPLOAD_DIR

# -------------------------- Celery --------------------------
from app.celery_app import celery_app  # Убедись, что у тебя есть этот файл!

router = APIRouter()

# ---------------------------------------------------------
# TASK STATUS ENUM
# ---------------------------------------------------------
class TaskStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing"
    EXTRACTING = "extracting"
    CLEANING = "cleaning"
    CLASSIFYING = "classifying"
    STRUCTURE = "structure"
    GENERATING = "generating"      # Новый этап
    READY = "ready"
    ERROR = "error"
    QUEUED = "queued"


# Глобальное хранилище статуса (в продакшене лучше Redis, но пока в памяти как у тебя было)
task_status: Dict[str, dict] = {}


def set_status(task_id: str, status: TaskStatus, progress: int = None, eta_min: int = None, details: dict = None, msg: str = None):
    task_status[task_id] = {
        "task_id": task_id,
        "status": status.value,
        "progress": progress if progress is not None else (task_status.get(task_id, {}).get("progress", 0)),
        "eta_min": eta_min,
        "details": details or {},
        "message": msg,
        "updated_at": datetime.utcnow().isoformat()
    }
    logger.info(f"[STATUS] {task_id} → {status.value} | progress: {task_status[task_id]['progress']}%")


# ---------------------------------------------------------
# 1. STAGE 1: Upload + Initial Analysis (быстро!)
# ---------------------------------------------------------
@router.post("/analyze/init")
async def analyze_init(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, detail="Only PDF files are supported")

    task_id = str(uuid.uuid4())
    filename = f"{task_id}.pdf"
    input_path = os.path.join(UPLOAD_DIR, filename)

    # Сохраняем файл
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(input_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        set_status(task_id, TaskStatus.EXTRACTING, progress=10)

        # Быстрые метаданные
        pages = extract_pdf_pages(input_path)
        page_total = len(pages)

        full_text = await extract_pdf_text(input_path)
        logger.info(f"[TEXT] Extracted: {len(full_text)} chars")

        cleaned = clean_text(full_text)
        logger.info(f"[TEXT] Cleaning finished, length={len(cleaned)}")

        # Язык
        try:
            from langdetect import detect
            document_language = detect(cleaned[:5000]) if cleaned.strip() else "en"
        except:
            document_language = "en"
        logger.info(f"[LANG] → {document_language}")

        # Лёгкая классификация (или хардкод heuristic)
        try:
            classification = classify_document(cleaned)
            recommended_days = classification.get("recommended_days", 10)
        except:
            recommended_days = 10 if len(cleaned) > 50000 else 5

        size_mb = os.path.getsize(input_path) / (1024 * 1024)

        # Сохраняем начальный анализ для generate
        init_data = {
            "original_file": filename,
            "pages": page_total,
            "length_chars": len(cleaned),
            "document_language": document_language,
            "size_mb": round(size_mb, 2)
        }
        init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
        with open(init_path, "w", encoding="utf-8") as f:
            json.dump(init_data, f)

        set_status(task_id, TaskStatus.READY, progress=100, eta_min=0)

        return {
            "task_id": task_id,
            "pages": page_total,
            "detected_language": document_language.upper(),
            "size_mb": round(size_mb, 2),
            "suggested_plan": {
                "days": recommended_days,
                "hours_per_day": 3
            },
            "estimated_processing_time_min": recommended_days * 2  # примерная оценка
        }

    except Exception as e:
        logger.error(f"[INIT FAILED] {task_id}: {e}")
        set_status(task_id, TaskStatus.ERROR, msg=str(e))
        send_telegram_alert(f"INIT FAILED\nTask: {task_id}\nError: {e}")
        raise HTTPException(500, detail="Initial analysis failed")


# ---------------------------------------------------------
# 2. STAGE 2: Start Full Generation (асинхронно)
# ---------------------------------------------------------
@router.post("/analyze/generate")
async def start_generate(
    task_id: str = Body(..., embed=True),
    days: int = Body(10),
    hours_per_day: int = Body(3)
):
    init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
    if not os.path.exists(init_path):
        raise HTTPException(404, detail="Task not found or init not completed")

    # Ставим в очередь
    set_status(task_id, TaskStatus.QUEUED, progress=0, eta_min=days * 2)

    # Запускаем Celery задачу
    celery_app.send_task(
        "app.tasks.full_generation",
        args=[task_id, days, hours_per_day]
    )

    return {"task_id": task_id, "status": "queued"}


# ---------------------------------------------------------
# 3. STATUS
# ---------------------------------------------------------
@router.get("/analyze/status/{task_id}")
def get_status(task_id: str):
    status_data = task_status.get(task_id)
    if not status_data:
        raise HTTPException(404, detail="Task not found")

    response = {
        "status": status_data["status"],
        "progress": status_data["progress"],
    }
    if "eta_min" in status_data and status_data["eta_min"] is not None:
        response["eta_min"] = status_data["eta_min"]

    # Если завершено — добавляем result_url (потом сделаешь S3 или локальный)
    if status_data["status"] == "ready":
        result_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.pdf")
        if os.path.exists(result_path):
            # Замени на свой домен или signed URL
            response["result_url"] = f"https://learnscaffold-backend.onrender.com/download/{task_id}"

    return response


# ---------------------------------------------------------
# 4. EMAIL NOTIFICATION
# ---------------------------------------------------------
@router.post("/notify/email")
async def notify_email(task_id: str = Body(...), email: str = Body(...)):
    # Сохраняем email в статус (или отдельно)
    current = task_status.get(task_id, {})
    current["email"] = email
    task_status[task_id] = current

    # Можно сохранить в файл или Redis
    email_path = os.path.join(UPLOAD_DIR, f"{task_id}_email.txt")
    with open(email_path, "w") as f:
        f.write(email)

    return {"status": "ok"}


# ---------------------------------------------------------
# LEGACY: Старый /analyze и /analyze/ — оставляем для совместимости
# ---------------------------------------------------------
@router.post("/analyze")
@router.post("/analyze/")
async def analyze_legacy(payload=Body(...)):
    # Можно вызвать старый код или вернуть предупреждение
    return {
        "warning": "Legacy endpoint. Use /analyze/init + /analyze/generate for better experience.",
        "redirect_to": "new_flow"
    }


# ---------------------------------------------------------
# GET STATUS LEGACY (совместимость)
# ---------------------------------------------------------
@router.get("/analyze/status/{file_id}/")
@router.get("/analyze/status/{file_id}")
def get_status_legacy(file_id: str):
    # Поддержка старых file_id (если они совпадают с task_id)
    return get_status(file_id)
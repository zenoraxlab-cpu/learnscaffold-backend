# app/tasks.py

import os
import json
from datetime import datetime

from app.celery_app import celery_app
from app.utils.logger import logger

from app.services.pdf_extractor import extract_pdf_text
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.structure_extractor import (
    extract_structure_from_text,
    extract_structure,
)
from app.services.pdf_text import extract_clean_text
from app.services.notifier import send_telegram_alert

# ⚠️ ВАЖНО: путь БЕЗ routes
BASE_UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data")

# Опционально: LLM fallback
try:
    from app.services.llm_structure import extract_structure_llm
except ImportError:
    extract_structure_llm = None


@celery_app.task(name="app.tasks.full_generation")
def full_generation(task_id: str, days: int, hours_per_day: int):
    """
    Диагностически ЧИСТАЯ Celery-задача.
    Никакого FastAPI, никакого UI, только вычисления и логи.
    """
    try:
        logger.info(f"[TASK START] {task_id}")

        init_path = os.path.join(BASE_UPLOAD_DIR, f"{task_id}_init.json")
        if not os.path.exists(init_path):
            raise FileNotFoundError(f"Init file not found: {init_path}")

        with open(init_path, "r", encoding="utf-8") as f:
            init_data = json.load(f)

        filename = init_data["original_file"]
        input_path = os.path.join(BASE_UPLOAD_DIR, filename)
        document_language = init_data.get("document_language", "en")

        # -------- STEP 1: TEXT EXTRACTION --------
        logger.info("[TASK] step 1: extract text")

        full_text = extract_pdf_text(input_path)
        cleaned = clean_text(full_text)

        # -------- STEP 2: CLASSIFICATION --------
        logger.info("[TASK] step 2: classify")

        try:
            classification = classify_document(cleaned)
        except Exception as e:
            logger.error(f"[CLASSIFY FAILED] {e}")
            classification = {
                "document_type": "text",
                "main_topics": [],
                "summary": "Classification failed",
            }

        # -------- STEP 3: STRUCTURE --------
        logger.info("[TASK] step 3: structure")

        structure = []

        try:
            structure = extract_structure(input_path) or []
            logger.info(f"[STRUCTURE] PDF headings: {len(structure)}")
        except Exception as e:
            logger.warning(f"[STRUCTURE] PDF failed: {e}")

        if len(structure) < 3:
            logger.info("[STRUCTURE] fallback → regex")
            try:
                text_by_page = extract_clean_text(input_path)
                structure = extract_structure_from_text(text_by_page)
            except Exception as e:
                logger.warning(f"[STRUCTURE fallback failed] {e}")

        if not structure and extract_structure_llm:
            logger.info("[STRUCTURE] fallback → LLM")
            try:
                structure = extract_structure_llm(
                    cleaned[:200_000], document_language
                )
            except Exception as e:
                logger.error(f"[LLM STRUCTURE FAILED] {e}")

        # -------- STEP 4: SAVE RESULT --------
        logger.info("[TASK] step 4: save result")

        final_data = {
            "task_id": task_id,
            "generated_at": datetime.utcnow().isoformat(),
            "plan": {
                "days": days,
                "hours_per_day": hours_per_day,
            },
            "document_type": classification.get("document_type"),
            "main_topics": classification.get("main_topics", []),
            "summary": classification.get("summary", ""),
            "structure": structure,
            "document_language": document_language,
        }

        result_path = os.path.join(
            BASE_UPLOAD_DIR, f"{task_id}_analysis.json"
        )

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        logger.info(f"[TASK SUCCESS] {task_id}")

        return {"status": "ok", "task_id": task_id}

    except Exception as e:
        logger.error(f"[TASK FAILED] {task_id}: {e}")
        logger.exception(e)
        send_telegram_alert(
            f"Celery task FAILED\nTask: {task_id}\nError: {str(e)}"
        )
        raise

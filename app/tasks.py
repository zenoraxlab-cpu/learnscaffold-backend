# app/tasks.py

from app.celery_app import celery_app
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure_from_text, extract_structure
from app.services.pdf_text import extract_clean_text
from app.services.notifier import send_telegram_alert
from app.routes.analyze import set_status, TaskStatus, UPLOAD_DIR
import os
import json
from datetime import datetime

# Опционально: если есть LLM fallback
try:
    from app.services.llm_structure import extract_structure_llm
except ImportError:
    extract_structure_llm = None


@celery_app.task(name="app.tasks.full_generation")
def full_generation(task_id: str, days: int, hours_per_day: int):
    """
    Тяжёлая часть: classify + structure extraction + генерация финального результата
    Здесь обновляем прогресс, чтобы фронт видел движение
    """
    try:
        logger.info(f"[TASK START] full_generation → {task_id} | Plan: {days} days × {hours_per_day}h")

        init_path = os.path.join(UPLOAD_DIR, f"{task_id}_init.json")
        if not os.path.exists(init_path):
            raise FileNotFoundError("Init data not found")

        with open(init_path, "r", encoding="utf-8") as f:
            init_data = json.load(f)

        filename = init_data["original_file"]
        input_path = os.path.join(UPLOAD_DIR, filename)
        document_language = init_data["document_language"]

        # Шаг 1: Повторно извлекаем текст (уже есть в init, но на всякий)
        set_status(task_id, TaskStatus.CLASSIFYING, progress=10, eta_min=days * 2)
        full_text = extract_pdf_text.sync(input_path) if hasattr(extract_pdf_text, 'sync') else "cached_text"  # если async — адаптируй
        cleaned = clean_text(full_text)

        # Шаг 2: Классификация
        try:
            classification = classify_document(cleaned)
        except Exception as ce:
            logger.error(f"[CLASSIFY FAILED] {ce}")
            classification = {
                "document_type": "text",
                "main_topics": [],
                "summary": "Classification failed.",
                "recommended_days": days
            }

        # Шаг 3: Структура (самая тяжёлая часть)
        set_status(task_id, TaskStatus.STRUCTURE, progress=30, eta_min=days)

        structure = []

        # 1. PDF headings
        try:
            structure = extract_structure(input_path) or []
            if structure:
                logger.info(f"[STRUCTURE] PDF headings: {len(structure)}")
        except Exception as se:
            logger.warning(f"[STRUCTURE] PDF failed: {se}")

        # 2. Fallback regex
        if len(structure) < 3:
            logger.info("[STRUCTURE] Fallback → regex")
            try:
                text_by_page = extract_clean_text(input_path)
                structure = extract_structure_from_text(text_by_page)
            except Exception as re:
                logger.warning(f"[FALLBACK STRUCTURE] failed: {re}")

        # 3. Final LLM fallback
        if not structure and extract_structure_llm:
            logger.info("[STRUCTURE] Final fallback → LLM")
            try:
                structure = extract_structure_llm(cleaned[:200000], document_language) or []
            except Exception as le:
                logger.error(f"[LLM_STRUCTURE] failed: {le}")

        # Шаг 4: Генерация финального результата (здесь ты делаешь PDF или JSON)
        set_status(task_id, TaskStatus.GENERATING, progress=70, eta_min=3)

        # Пример: сохраняем полный анализ
        final_data = {
            "task_id": task_id,
            "generated_at": datetime.utcnow().isoformat(),
            "plan": {"days": days, "hours_per_day": hours_per_day},
            "document_type": classification.get("document_type", "text"),
            "main_topics": classification.get("main_topics", []),
            "summary": classification.get("summary", ""),
            "structure": structure,
            "document_language": document_language,
            "pages": init_data["pages"],
            "length_chars": init_data["length_chars"],
        }

        # Сохраняем JSON (потом можешь генерить PDF из этого)
        result_path = os.path.join(UPLOAD_DIR, f"{task_id}_analysis.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        # Здесь можешь добавить генерацию PDF (например, WeasyPrint, ReportLab и т.д.)
        # final_pdf_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.pdf")
        # generate_pdf_from_data(final_data, final_pdf_path)

        # Финал
        set_status(task_id, TaskStatus.READY, progress=100, eta_min=0)
        logger.info(f"[TASK SUCCESS] {task_id} → READY")

        # Email уведомление, если пользователь подписался
        email_path = os.path.join(UPLOAD_DIR, f"{task_id}_email.txt")
        if os.path.exists(email_path):
            with open(email_path, "r") as f:
                email = f.read().strip()
            try:
                # Замени на свой email-сервис (SMTP, SendGrid и т.д.)
                logger.info(f"Sending email to {email}")
                # send_email(email, "Your LearnScaffold is ready!", f"Download: https://yourdomain/download/{task_id}")
            except Exception as ee:
                logger.error(f"Email send failed: {ee}")
                send_telegram_alert(f"Email failed for {task_id}")

    except Exception as e:
        logger.error(f"[TASK FAILED] {task_id}: {e}")
        logger.exception(e)
        set_status(task_id, TaskStatus.ERROR, progress=0, msg=str(e))
        send_telegram_alert(f"FULL GENERATION FAILED\nTask: {task_id}\nError: {str(e)}")
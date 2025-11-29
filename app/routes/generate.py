from fastapi import APIRouter, HTTPException
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text
from app.services.structure_extractor import extract_structure
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.llm_study import generate_day_plan
from app.config import UPLOAD_DIR
import os

router = APIRouter()


@router.post("/study")
async def generate_study_plan(file_id: str, days: int = 14):
    """
    Генерация Study Mode учебного плана:
    1) Находит файл
    2) Извлекает ПОЛНУЮ структуру: главы + страницы
    3) Извлекает текст
    4) Чистит и делит на чанки
    5) Классифицирует документ
    6) Генерирует учебный план на days дней
    """

    logger.info(f"[GENERATE] Study plan request: file_id={file_id}, days={days}")

    # -----------------------------------------------------------
    # 1. Ищем файл
    # -----------------------------------------------------------
    file_path = None
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    # -----------------------------------------------------------
    # 2. Структура документа (главы+страницы)
    # -----------------------------------------------------------
    structure = extract_structure(file_path)
    if not structure:
        logger.warning("[GENERATE] Structure extraction failed, falling back to simple text")
        structure = []

    # -----------------------------------------------------------
    # 3. Извлечение и очистка текста
    # -----------------------------------------------------------
    raw_text = extract_pdf_text(file_path)
    cleaned = clean_text(raw_text)

    chunks = chunk_text(cleaned, max_chars=2500, overlap=200)

    if not chunks:
        raise HTTPException(status_code=500, detail="Failed to chunk text")

    # -----------------------------------------------------------
    # 4. Классификация по первому чанку
    # -----------------------------------------------------------
    analysis = classify_document(chunks[0])

    # -----------------------------------------------------------
    # 5. Генерация учебного плана по дням
    # -----------------------------------------------------------
    plan = []
    for day in range(1, days + 1):
        lesson = generate_day_plan(
            day_number=day,
            total_days=days,
            document_type=analysis["document_type"],
            main_topics=analysis["main_topics"],
            summary=analysis["summary"],
            structure=structure  # <---- вот здесь используется структура
        )
        plan.append(lesson)

    logger.info("[GENERATE] Study plan generated successfully")

    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": analysis,
        "structure": structure,
        "plan": {"days": plan},
    }

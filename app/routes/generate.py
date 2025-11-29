from fastapi import APIRouter, HTTPException
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text
from app.services.structure_extractor import extract_structure
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.llm_study import generate_day_plan
from app.services.llm_flashcards import generate_flashcards_for_lesson
from app.config import UPLOAD_DIR
import os

router = APIRouter()


def build_lesson_context(lesson: dict) -> str:
    """
    Собираем текстовый контент урока для генерации флешкарт.
    Аккуратно обрабатываем строки и списки.
    """
    parts: list[str] = []

    title = lesson.get("title")
    if title:
        parts.append(f"Title: {title}")

    theory = lesson.get("theory")
    if theory:
        # theory может быть строкой или списком
        if isinstance(theory, list):
            theory_text = "\n".join(str(t) for t in theory)
        else:
            theory_text = str(theory)
        parts.append("Theory:\n" + theory_text)

    practice = lesson.get("practice")
    if practice:
        # practice часто бывает списком задач
        if isinstance(practice, list):
            practice_text = "\n".join(f"- {str(p)}" for p in practice)
        else:
            practice_text = str(practice)
        parts.append("Practice:\n" + practice_text)

    summary = lesson.get("summary")
    if summary:
        if isinstance(summary, list):
            summary_text = "\n".join(str(s) for s in summary)
        else:
            summary_text = str(summary)
        parts.append("Summary:\n" + summary_text)

    return "\n\n".join(parts)


@router.post("/study")
async def generate_study_plan(
    file_id: str,
    days: int = 14,
    include_flashcards: bool = False,
    flashcards_per_lesson: int = 5,
):
    """
    Генерация Study Mode учебного плана:
    1) Находит файл
    2) Извлекает ПОЛНУЮ структуру: главы + страницы
    3) Извлекает текст
    4) Чистит и делит на чанки
    5) Классифицирует документ
    6) Генерирует учебный план на days дней
    7) (опционально) Генерирует flashcards для каждого дня
    """

    logger.info(
        f"[GENERATE] Study plan request: file_id={file_id}, days={days}, "
        f"include_flashcards={include_flashcards}, flashcards_per_lesson={flashcards_per_lesson}"
    )

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
    # 5. Генерация учебного плана по дням + флешкарты
    # -----------------------------------------------------------
    plan = []
    for day in range(1, days + 1):
        lesson = generate_day_plan(
            day_number=day,
            total_days=days,
            document_type=analysis["document_type"],
            main_topics=analysis["main_topics"],
            summary=analysis["summary"],
            structure=structure,  # <---- здесь используется структура
        )

        # --- 5.1. Генерация flashcards поверх урока (если включено) ---
        if include_flashcards:
            content = build_lesson_context(lesson)
            if content.strip():
                lesson["flashcards"] = generate_flashcards_for_lesson(
                    content=content,
                    language=analysis.get("language", "en"),
                    count=flashcards_per_lesson,
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

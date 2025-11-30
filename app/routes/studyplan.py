from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.schemas.studyplan import PlanPdfRequest
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
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
        if isinstance(theory, list):
            theory_text = "\n".join(str(t) for t in theory)
        else:
            theory_text = str(theory)
        parts.append("Theory:\n" + theory_text)

    practice = lesson.get("practice")
    if practice:
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
    2) Извлекает структуру (главы+страницы)
    3) Извлекает текст
    4) Чистит и делит на чанки
    5) Классифицирует документ
    6) Генерирует учебный план на days дней
    7) (опционально) флешкарты
    8) Равномерно размазывает страницы PDF по дням → source_pages
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
        logger.warning("[GENERATE] Structure extraction failed, using empty structure")
        structure = []

    # -----------------------------------------------------------
    # 3. Извлечение страниц (для привязки уроков к страницам)
    # -----------------------------------------------------------
    try:
        pages = extract_pdf_pages(file_path)
        pages_count = len(pages)
        logger.info(f"[GENERATE] PDF pages extracted: {pages_count}")
    except Exception:
        logger.exception("[GENERATE] Failed to extract PDF pages")
        pages = []
        pages_count = 0

    # -----------------------------------------------------------
    # 4. Извлечение и очистка текста
    # -----------------------------------------------------------
    raw_text = extract_pdf_text(file_path)
    cleaned = clean_text(raw_text)

    chunks = chunk_text(cleaned, max_chars=2500, overlap=200)
    if not chunks:
        raise HTTPException(status_code=500, detail="Failed to chunk text")

    # -----------------------------------------------------------
    # 5. Классификация по первому чанку
    # -----------------------------------------------------------
    analysis = classify_document(chunks[0])

    # -----------------------------------------------------------
    # 6. Подготовка разбиения страниц по дням
    # -----------------------------------------------------------
    # Страницы считаем 1..pages_count
    if pages_count > 0 and days > 0:
        base_per_day = pages_count // days
        extra = pages_count % days
    else:
        base_per_day = 0
        extra = 0

    def get_pages_for_day(day_number: int) -> list[int]:
        """
        Равномерно распределяем страницы по дням:
        первые `extra` дней получают (base_per_day + 1) страниц,
        остальные — base_per_day.
        """
        if pages_count == 0 or days <= 0:
            return []

        day_idx = day_number - 1  # 0-based

        prev_days = day_idx
        pages_before = prev_days * base_per_day + min(prev_days, extra)

        curr_count = base_per_day + (1 if day_idx < extra else 0)
        if curr_count <= 0:
            return []

        start_page = pages_before + 1
        end_page = pages_before + curr_count

        start_page = max(1, start_page)
        end_page = min(pages_count, end_page)

        if start_page > end_page:
            return []

        return list(range(start_page, end_page + 1))

    # -----------------------------------------------------------
    # 7. Генерация учебного плана по дням + флешкарты + source_pages
    # -----------------------------------------------------------
    plan = []
    for day in range(1, days + 1):
        lesson = generate_day_plan(
            day_number=day,
            total_days=days,
            document_type=analysis["document_type"],
            main_topics=analysis["main_topics"],
            summary=analysis["summary"],
            structure=structure,
        )

        # Привязка к страницам оригинального PDF
        pages_for_day = get_pages_for_day(day)
        lesson["source_pages"] = pages_for_day
        logger.info(f"[GENERATE] Day {day}: source_pages={pages_for_day}")

        # Флешкарты (если включены)
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


@router.post("/pdf")
async def generate_plan_pdf(payload: PlanPdfRequest):
    """
    Принимает от фронтенда текст учебного плана и возвращает PDF-файл.
    Используем шрифт DejaVuSans для нормальных русских букв.
    """
    buf = BytesIO()

    # шрифт лежит в app/fonts/DejaVuSans.ttf (вы уже его копировали)
    pdfmetrics.registerFont(TTFont("DejaVu", "app/fonts/DejaVuSans.ttf"))

    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    text_object = pdf.beginText(40, height - 50)
    text_object.setFont("DejaVu", 11)

    for line in payload.content.splitlines():
        # Переход на новую страницу, если вышли за нижнее поле
        if text_object.getY() < 60:
            pdf.drawText(text_object)
            pdf.showPage()
            text_object = pdf.beginText(40, height - 50)
            text_object.setFont("DejaVu", 11)

        text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    buf.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="study-plan-{payload.days}-days.pdf"'
    }

    return StreamingResponse(buf, media_type="application/pdf", headers=headers)

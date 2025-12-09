from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis
from app.services.notifier import send_telegram_alert

router = APIRouter()

# ---------------------------------------------------------------------
# 1. Делим структуру по линейным диапазонам
# ---------------------------------------------------------------------
def split_structure_into_ranges(structure, total_pages, days):
    """
    Делит общее количество страниц по дням равномерно.
    Возвращает список: [(1, 80), (81, 160), ...]
    """

    pages_per_day = max(total_pages // days, 1)
    ranges = []

    for i in range(days):
        start = i * pages_per_day + 1
        end = (i + 1) * pages_per_day
        if i == days - 1:
            end = total_pages
        ranges.append(range(start, end + 1))

    return ranges

# ---------------------------------------------------------------------
# 2. Нормализация плана
# ---------------------------------------------------------------------
def normalize_plan(raw):
    """
    Приводим любой формат LLM → list[dict].
    """
    if isinstance(raw, dict):
        if isinstance(raw.get("plan"), dict):
            days = raw["plan"].get("days")
            if isinstance(days, list):
                return days
        if isinstance(raw.get("plan"), list):
            return raw["plan"]

    if isinstance(raw, list):
        return raw

    logger.error(f"[ERROR] Unexpected plan format: {raw}")
    raise HTTPException(status_code=500, detail="Invalid plan format returned by LLM")

# ---------------------------------------------------------------------
# 3. Основной endpoint /generate
# ---------------------------------------------------------------------
@router.post("")
@router.post("/")
async def generate(payload: dict):

    print("🔥🔥🔥 BACKEND /generate CALLED 🔥🔥🔥")
    logger.warning(f"[DEBUG PAYLOAD] {payload}")

    file_id = payload.get("file_id")
    days = payload.get("days")
    language = payload.get("language")

    if not file_id or days is None or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    try:
        days = int(days)
    except:
        raise HTTPException(status_code=422, detail="Invalid 'days' value")

    logger.info(f"[GENERATE] Start: file_id={file_id} days={days} lang={language}")

    # Загружаем анализ
    try:
        analysis = load_saved_analysis(file_id)
    except Exception:
        raise HTTPException(status_code=404, detail="No saved analysis for this file")

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])
    document_language = analysis.get("document_language", "en")

    logger.warning(f"[DEBUG STRUCTURE] {structure}")

    try:
        raw_plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        plan_days = normalize_plan(raw_plan)

        # Линейная разметка страниц
        all_pages = [p for block in structure for p in block.get("pages", [])]
        total_pages = max(all_pages) if all_pages else 1
        page_ranges = split_structure_into_ranges(structure, total_pages, days)

        for i, lesson in enumerate(plan_days):
            lesson["source_pages"] = list(page_ranges[i])

        debug_titles = [d.get("title") for d in plan_days]
        debug_pages = [d.get("source_pages") for d in plan_days]

        logger.warning(f"[DEBUG TITLES] {debug_titles}")
        logger.warning(f"[DEBUG PAGES] {debug_pages}")

        return {
            "status": "ok",
            "file_id": file_id,
            "days": days,
            "analysis": analysis,
            "plan": {"days": plan_days},
            "debug_structure": structure,
            "debug_titles": debug_titles,
            "debug_pages_attached": debug_pages,
        }

    except Exception as e:
        logger.error("=== GENERATE FAILED ===")
        logger.exception(e)

        try:
            send_telegram_alert(
                f"❗ GENERATE FAILED\n"
                f"File ID: {file_id}\n"
                f"Ошибка: {str(e)}\n"
                f"Нужна ручная генерация плана."
            )
        except Exception as te:
            logger.error(f"Telegram notifier error: {te}")

        return {
            "status": "delayed",
            "file_id": file_id,
            "message": (
                "Your study plan requires extended processing. "
                "We will send it to your email when it is ready."
            ),
        }

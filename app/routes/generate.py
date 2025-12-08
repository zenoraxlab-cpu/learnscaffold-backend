from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis
from app.services.notifier import send_telegram_alert

router = APIRouter()

# ---------------------------------------------------------------------
# 1. Page mapping: match lesson titles ↔ structure titles/topics
# ---------------------------------------------------------------------
def attach_source_pages(plan_days, structure):
    """
    Привязывает PDF-страницы к урокам.
    """
    indexed = []

    # Подготовка структуры
    for block in structure:
        title = (block.get("title") or "").lower().strip()
        topics = block.get("topics") or []
        pages = block.get("pages") or []

        if not pages:
            continue

        tokens = set(title.replace(",", " ").replace(";", " ").split())
        for t in topics:
            tokens.update(str(t).lower().split())

        indexed.append({
            "title": title,
            "tokens": tokens,
            "pages": pages
        })

    # Привязка страниц
    for lesson in plan_days:
        lt = (lesson.get("title") or "").lower().strip()
        lt_tokens = set(lt.replace(",", " ").replace(";", " ").split())

        matched = []

        for item in indexed:
            struct_title = item["title"]

            # прямое совпадение по заголовку
            if struct_title in lt or lt in struct_title:
                matched.extend(item["pages"])
                continue

            # ≥2 общих токена — считаем, что это один и тот же блок
            if len(lt_tokens.intersection(item["tokens"])) >= 2:
                matched.extend(item["pages"])

        lesson["source_pages"] = sorted(set(matched))

    return plan_days


# ---------------------------------------------------------------------
# 2. Нормализация плана
# ---------------------------------------------------------------------
def normalize_plan(raw):
    """
    Любой формат → list[dict].
    """

    if isinstance(raw, dict):
        # { "plan": { "days": [...] } }
        if isinstance(raw.get("plan"), dict):
            days = raw["plan"].get("days")
            if isinstance(days, list):
                return days

        # { "plan": [ ... ] }
        if isinstance(raw.get("plan"), list):
            return raw["plan"]

    # Уже список
    if isinstance(raw, list):
        return raw

    logger.error(f"[ERROR] Unexpected plan format: {raw}")
    raise HTTPException(status_code=500, detail="Invalid plan format returned by LLM")


# ---------------------------------------------------------------------
# 3. Основной endpoint: /generate
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

    # ----------------- ОСНОВНОЙ TRY -----------------
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
        plan_days = attach_source_pages(plan_days, structure)

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

    # ----------------- ФОЛБЭК ДЛЯ LLM -----------------
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

        # Не роняем 500, а отдаём delayed → фронт потом адаптируем
        return {
            "status": "delayed",
            "file_id": file_id,
            "message": (
                "Your study plan requires extended processing. "
                "We will send it to your email when it is ready."
            ),
        }

from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis

router = APIRouter()


# ---------------------------------------------------------------------
# 1. Page mapping: match lesson titles ↔ structure titles/topics
# ---------------------------------------------------------------------
def attach_source_pages(plan_days, structure):
    """
    Привязывает PDF-страницы к урокам на основе структуры вида:
    {
        "title": "Chapter...",
        "topics": ["...", "..."],
        "pages": [3,4,5]
    }
    """

    indexed = []

    # Подготовка структуры
    for block in structure:
        title = (block.get("title") or "").lower().strip()
        topics = block.get("topics") or []
        pages = block.get("pages") or []

        if not pages:
            continue  # пропускаем блоки без страниц

        # Создаём набор токенов (title + topics)
        tokens = set(title.replace(",", " ").replace(";", " ").split())
        for t in topics:
            tokens.update(str(t).lower().split())

        indexed.append({
            "title": title,
            "tokens": tokens,
            "pages": pages
        })

    # Привязка страниц к каждому уроку
    for lesson in plan_days:
        lt = (lesson.get("title") or "").lower().strip()
        lt_tokens = set(lt.replace(",", " ").replace(";", " ").split())

        matched = []

        for item in indexed:
            struct_title = item["title"]

            # 1) Прямое совпадение по заголовку
            if struct_title in lt or lt in struct_title:
                matched.extend(item["pages"])
                continue

            # 2) ≥2 общих токена → семантический матч
            if len(lt_tokens.intersection(item["tokens"])) >= 2:
                matched.extend(item["pages"])

        # Уникальные страницы
        lesson["source_pages"] = sorted(set(matched))

    return plan_days


# ---------------------------------------------------------------------
# 2. Нормализация плана (любой формат → list)
# ---------------------------------------------------------------------
def normalize_plan(raw):
    """
    Приводит результат LLM к формату list[dict].
    Поддерживает:
      - { plan: { days: [...] } }
      - { plan: [...] }
      - [ ... ]
    """

    if isinstance(raw, dict):

        # { "plan": { "days": [...] } }
        if "plan" in raw and isinstance(raw["plan"], dict):
            days = raw["plan"].get("days")
            if isinstance(days, list):
                return days

        # { "plan": [ ... ] }
        if "plan" in raw and isinstance(raw["plan"], list):
            return raw["plan"]

    # План уже является списком
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

    # Проверка входа
    if not file_id or days is None or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    try:
        days = int(days)
    except:
        raise HTTPException(status_code=422, detail="Invalid 'days' value")

    logger.info(f"[GENERATE] Start: file_id={file_id} days={days} lang={language}")

    # Загружаем анализ из /analyze
    analysis = load_saved_analysis(file_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No saved analysis for this file")

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])
    document_language = analysis.get("document_language", "en")

    logger.warning(f"[DEBUG STRUCTURE] {structure}")

    try:
        # Вызываем LLM (генерация дневного плана)
        raw_plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        # Приведение формата
        plan_days = normalize_plan(raw_plan)

        # Привязываем страницы
        plan_days = attach_source_pages(plan_days, structure)

        # Debug
        debug_titles = [d.get("title") for d in plan_days]
        debug_pages = [d.get("source_pages") for d in plan_days]

        logger.warning(f"[DEBUG TITLES] {debug_titles}")
        logger.warning(f"[DEBUG PAGES] {debug_pages}")

        # Итоговый ответ
        return {
            "status": "ok",
            "file_id": file_id,
            "days": days,
            "analysis": analysis,
            "plan": {"days": plan_days},

            # DEBUG
            "debug_structure": structure,
            "debug_titles": debug_titles,
            "debug_pages_attached": debug_pages,
        }

    except Exception as e:
        logger.error("[GENERATE] LLM generation failed")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

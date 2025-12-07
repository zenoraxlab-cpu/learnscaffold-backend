from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis

router = APIRouter()


# ---------------------------------------------------------------------
# 1. Smart fuzzy matching: topic → PDF page
# ---------------------------------------------------------------------
def attach_source_pages(plan_days, structure):
    """
    Привязка страниц PDF к урокам по смыслу:
      ✔ подстрока
      ✔ пересечение ключевых слов
    """

    indexed = []

    # Подготовка структуры тем из анализа
    for block in structure:
        topic = block.get("topic")
        page = block.get("page")
        if not topic or not page:
            continue

        topic_l = topic.lower()

        indexed.append({
            "topic": topic_l,
            "tokens": set(topic_l.replace(",", " ").replace(";", " ").split()),
            "page": page
        })

    # Привязка страниц к каждому уроку
    for lesson in plan_days:
        title = (lesson.get("title") or "").lower()
        title_tokens = set(title.replace(",", " ").replace(";", " ").split())
        matched = []

        for item in indexed:
            topic = item["topic"]

            # 1) Прямое совпадение по подстроке
            if topic in title or title in topic:
                matched.append(item["page"])
                continue

            # 2) Семантическое совпадение по токенам
            if len(title_tokens.intersection(item["tokens"])) >= 2:
                matched.append(item["page"])

        lesson["source_pages"] = sorted(set(matched))

    return plan_days


# ---------------------------------------------------------------------
# 2. Универсальный парсер структуры плана (любой формат → days[])
# ---------------------------------------------------------------------
def normalize_plan(raw_plan):
    """
    Приводит план от LLM к универсальному виду:
      → всегда возвращает list[dict]
    """

    # Формат: { "plan": { "days": [...] } }
    if isinstance(raw_plan, dict) and "plan" in raw_plan and isinstance(raw_plan["plan"], dict):
        return raw_plan["plan"].get("days", [])

    # Формат: { "plan": [ ... ] }
    if isinstance(raw_plan, dict) and isinstance(raw_plan.get("plan"), list):
        return raw_plan["plan"]

    # Формат: [...] (просто список уроков)
    if isinstance(raw_plan, list):
        return raw_plan

    logger.error(f"[ERROR] Unexpected plan format: {raw_plan}")
    raise HTTPException(status_code=500, detail="Invalid plan format")


# ---------------------------------------------------------------------
# 3. Основной endpoint /generate
# ---------------------------------------------------------------------
@router.post("")
@router.post("/")
async def generate(payload: dict):

    print("🔥🔥🔥 BACKEND /generate CALLED")
    logger.warning(f"[DEBUG PAYLOAD] {payload}")

    # -------- Проверка входных параметров ----------
    file_id = payload.get("file_id")
    days = payload.get("days")
    language = payload.get("language")

    if not file_id or days is None or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    try:
        days = int(days)
    except:
        raise HTTPException(status_code=422, detail="Invalid 'days' value")

    logger.info(f"[GENERATE] Start → file={file_id} days={days} lang={language}")

    # -------- Загрузка анализа из /analyze ----------
    analysis = load_saved_analysis(file_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No saved analysis for this file")

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])
    document_language = analysis.get("document_language", "en")

    logger.warning(f"[DEBUG STRUCTURE] {structure}")

    try:
        # -------- Генерация уроков через LLM --------
        raw_plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        # -------- Приведение формата плана --------
        plan_days = normalize_plan(raw_plan)

        # -------- Привязка страниц PDF --------
        plan_days = attach_source_pages(plan_days, structure)

        # -------- Debug поля --------
        debug_titles = [d.get("title") for d in plan_days]
        debug_pages = [d.get("source_pages") for d in plan_days]

        logger.warning(f"[DEBUG TITLES] {debug_titles}")
        logger.warning(f"[DEBUG PAGES] {debug_pages}")

        # -------- Возврат итогового ответа --------
        return {
            "status": "ok",
            "file_id": file_id,
            "days": days,
            "analysis": analysis,
            "plan": {"days": plan_days},

            # DEBUG FIELDS
            "debug_structure": structure,
            "debug_titles": debug_titles,
            "debug_pages_attached": debug_pages,
        }

    except Exception as e:
        logger.error("[GENERATE] LLM generation failed")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

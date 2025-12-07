from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis

router = APIRouter()


# ---------------------------------------------------------------------
# Fuzzy matching: привязка страниц PDF к урокам
# ---------------------------------------------------------------------
def attach_source_pages(plan_days, structure):
    """
    Привязка страниц PDF к урокам по смыслу.
    Используем:
      - сравнение по подстроке
      - сравнение по ключевым словам
    """

    indexed = []

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

    for lesson in plan_days:
        title = (lesson.get("title") or "").lower()
        title_tokens = set(title.replace(",", " ").replace(";", " ").split())

        matched = []

        for item in indexed:
            topic = item["topic"]

            # Подстрока (90% кейсов)
            if topic in title or title in topic:
                matched.append(item["page"])
                continue

            # Match по 2+ общим словам
            if len(title_tokens.intersection(item["tokens"])) >= 2:
                matched.append(item["page"])

        # Итог: уникальные страницы, отсортированные
        lesson["source_pages"] = sorted(set(matched))

    return plan_days


# allow POST /generate and POST /generate/
@router.post("")
@router.post("/")
async def generate(payload: dict):

    print("🔥🔥🔥 BACKEND /generate CALLED")
    logger.warning(f"[DEBUG PAYLOAD] payload={payload}")

    file_id = payload.get("file_id")
    days = payload.get("days")
    language = payload.get("language")

    if not file_id or days is None or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    try:
        days = int(days)
    except:
        raise HTTPException(status_code=422, detail="Invalid 'days' value")

    logger.info(f"[GENERATE] Start → file_id={file_id} days={days} language={language}")

    # Загружаем JSON анализа из /analyze
    analysis = load_saved_analysis(file_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No saved analysis for this file")

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])
    document_language = analysis.get("document_language", "en")

    logger.warning(f"[DEBUG STRUCTURE] {structure}")

    try:
        # Генерируем уроки через LLM /services/llm_study.py
        plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        # -----------------------------
        # ДОБАВЛЯЕМ СТРАНИЦЫ (ВАЖНО!)
        # -----------------------------
        plan_days = plan.get("plan", {}).get("days", [])
        plan_days = attach_source_pages(plan_days, structure)
        plan["plan"]["days"] = plan_days

        # DEBUG
        debug_titles = [d.get("title") for d in plan_days]
        debug_pages = [d.get("source_pages") for d in plan_days]

        logger.warning(f"[DEBUG TITLES] {debug_titles}")
        logger.warning(f"[DEBUG PAGES] {debug_pages}")

        # Возвращаем план + debug
        return {
            **plan,
            "debug_structure": structure,
            "debug_titles": debug_titles,
            "debug_pages_attached": debug_pages,
        }

    except Exception as e:
        logger.error("[GENERATE] LLM generation failed")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

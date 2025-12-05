from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis

router = APIRouter()


@router.post("/generate/")
async def generate(payload: dict):

    print("🔥🔥🔥 BACKEND /generate CALLED 🔥🔥🔥")
    logger.warning(f"[DEBUG PAYLOAD] payload={payload}")

    """
    Generate full multi-day study plan based on previously saved analysis.
    Expects:
      - file_id: str
      - days: int
      - language: str (target language for the plan)
    """

    file_id = payload.get("file_id")
    days = payload.get("days")
    language = payload.get("language")


    # Basic validation
    if not file_id or days is None or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    try:
        days = int(days)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid 'days' value")

    logger.info(
        f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'"
    )

    # Load analysis JSON that was saved during /analyze
    analysis = load_saved_analysis(file_id)
    if not analysis:
        raise HTTPException(
            status_code=404, detail="No saved analysis for this file"
        )

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])
    document_language = analysis.get("document_language", "en")

    try:
        # Single LLM call that generates the whole plan
        plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        logger.info(f"[GENERATE] Completed successfully for file_id={file_id}")
        return plan

    except Exception as e:
        logger.error("[GENERATE] LLM generation failed")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=str(e))

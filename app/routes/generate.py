from fastapi import APIRouter, HTTPException
from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import load_saved_analysis

router = APIRouter()


@router.post("/generate/")
async def generate(payload: dict):

    file_id = payload.get("file_id")
    days = payload.get("days")
    language = payload.get("language")

    if not file_id or not days or not language:
        raise HTTPException(status_code=422, detail="Missing required parameters")

    logger.info(f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'")

    analysis = load_saved_analysis(file_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="No saved analysis for this file")

    summary = analysis.get("summary", "")
    structure = analysis.get("structure", [])

    try:
        plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
        )

        logger.info(f"[GENERATE] Completed successfully")
        return plan

    except Exception as e:
        logger.error("[GENERATE] LLM generation failed")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_study import generate_study_plan
from app.utils.logger import logger
import os
import json

router = APIRouter()

DATA_DIR = "/opt/render/project/src/data"


class GenerateRequest(BaseModel):
    file_id: str
    days: int
    language: str


@router.post("/generate/")
async def generate(request: GenerateRequest):
    file_id = request.file_id
    days = request.days
    language = request.language

    logger.info(f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'")

    # ---------------------------------------------
    # Load saved analysis from *_analysis.json
    # ---------------------------------------------
    analysis_path = os.path.join(DATA_DIR, f"{file_id}_analysis.json")

    if not os.path.exists(analysis_path):
        logger.error(f"[GENERATE] Missing analysis file → {analysis_path}")
        raise HTTPException(status_code=500, detail="Analysis data not found")

    try:
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read analysis: {e}")

    summary = analysis.get("summary", "")
    main_topics = analysis.get("main_topics", [])
    document_type = analysis.get("document_type", "document")
    level = analysis.get("level", "general")
    recommended_days = analysis.get("recommended_days", None)

    # ---------------------------------------------
    # CALL FIXED LLM FUNCTION WITH ALL PARAMETERS
    # ---------------------------------------------
    try:
        logger.info("[LLM_STUDY] Generating plan with full arguments...")
        plan = await generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            main_topics=main_topics,
        )
    except Exception as e:
        logger.exception("[GENERATE] LLM generation failed")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {e}")

    # ---------------------------------------------
    # RESPONSE
    # ---------------------------------------------
    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": {
            "summary": summary,
            "main_topics": main_topics,
            "document_type": document_type,
            "level": level,
            "recommended_days": recommended_days,
        },
        "plan": {"days": plan},
    }

# app/routes/generate.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.llm_study import generate_study_plan
from app.utils.logger import logger
import os
import json

router = APIRouter()

DATA_DIR = "/opt/render/project/src/data"


# --------------------------
# Request body model (FIX 422)
# --------------------------
class GenerateRequest(BaseModel):
    file_id: str
    days: int
    language: str


@router.post("/generate/")
async def generate(request: GenerateRequest):
    file_id = request.file_id
    days = request.days
    language = request.language

    logger.info(
        f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'"
    )

    # --------------------------
    # Load analysis data
    # --------------------------
    analysis_path = os.path.join(DATA_DIR, f"{file_id}_analysis.json")

    if not os.path.exists(analysis_path):
        logger.error(f"[GENERATE] Analysis file NOT FOUND → {analysis_path}")
        raise HTTPException(status_code=500, detail="Analysis data not found")

    try:
        with open(analysis_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read analysis data: {e}")

    summary = data.get("summary", "")
    main_topics = data.get("main_topics", [])
    document_type = data.get("document_type", "document")
    level = data.get("level", "general")
    recommended_days = data.get("recommended_days", None)

    # --------------------------
    # Generate plan with LLM
    # --------------------------
    try:
        logger.info(f"[LLM_STUDY] Generating full plan for {days} days...")
        plan = await generate_study_plan(file_id, days, language)
        logger.info(f"[LLM_STUDY] Plan generated: {days} days")
    except Exception as e:
        logger.exception("[GENERATE] LLM generation failed")
        raise HTTPException(status_code=500, detail=f"Plan generation failed: {e}")

    # --------------------------
    # Final response
    # --------------------------
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

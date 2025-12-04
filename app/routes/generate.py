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
    language: str   # пока игнорируется, но нужен для фронтенда


@router.post("/generate/")
async def generate(request: GenerateRequest):
    file_id = request.file_id
    days = request.days
    language = request.language   # может использоваться позже для выбора модели

    logger.info(f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'")

    # ------------------------------------------------------------
    # Load analysis
    # ------------------------------------------------------------
    analysis_path = os.path.join(DATA_DIR, f"{file_id}_analysis.json")

    if not os.path.exists(analysis_path):
        raise HTTPException(status_code=500, detail="Analysis file not found")

    try:
        with open(analysis_path, "r", encoding="utf-8") as f:
            analysis = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read analysis file: {e}")

    # Extract required fields
    document_type = analysis.get("document_type", "document")
    main_topics = analysis.get("main_topics", [])
    summary = analysis.get("summary", "")
    structure = analysis.get("structure", None)
    level = analysis.get("level", "general")
    recommended_days = analysis.get("recommended_days")

    # ------------------------------------------------------------
    # CALL LLM STUDY PLANNER (correct signature!)
    # ------------------------------------------------------------
    try:
        plan_days = generate_study_plan(
            total_days=days,
            document_type=document_type,
            main_topics=main_topics,
            summary=summary,
            structure=structure,
        )
    except Exception as e:
        logger.exception("[GENERATE] LLM generation failed")
        raise HTTPException(status_code=500, detail=f"Generation error: {e}")

    # ------------------------------------------------------------
    # Return response in unified frontend structure
    # ------------------------------------------------------------
    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": {
            "document_type": document_type,
            "main_topics": main_topics,
            "summary": summary,
            "level": level,
            "recommended_days": recommended_days,
        },
        "plan": {
            "days": plan_days
        }
    }

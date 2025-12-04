from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.routes.analyze import task_status
from app.config import UPLOAD_DIR
import os
import json

router = APIRouter()

# ---------------------------
# Request Model
# ---------------------------
class GenerateRequest(BaseModel):
    file_id: str
    days: int
    language: str = "en"


# ---------------------------
# Generate Study Plan
# ---------------------------
@router.post("/")
async def generate_plan(payload: GenerateRequest):

    file_id = payload.file_id
    days = payload.days
    language = payload.language

    logger.info(f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'")

    # ---------------------------------------------------
    # Validate analysis exists
    # ---------------------------------------------------
    analysis_data = task_status.get(file_id)
    if analysis_data != "ready":
        logger.error("[GENERATE] ERROR: Analysis not completed")
        raise HTTPException(status_code=400, detail="Analysis not completed")

    # ---------------------------------------------------
    # Locate analyzed data: structure + summary
    # ---------------------------------------------------
    analysis_file = os.path.join(UPLOAD_DIR, f"{file_id}_analysis.json")
    if not os.path.exists(analysis_file):
        raise HTTPException(status_code=500, detail="Analysis data not found")

    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", "")
    main_topics = data.get("main_topics", [])
    document_type = data.get("document_type", "document")
    structure = data.get("structure", [])

    # ---------------------------------------------------
    # Generate plan
    # ---------------------------------------------------
    try:
        plan = generate_study_plan(
            total_days=days,
            document_type=document_type,
            main_topics=main_topics,
            summary=summary,
            structure=structure,
        )

    except Exception as e:
        logger.error(f"[GENERATE] ERROR: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate study plan")

    logger.info("[GENERATE] Completed successfully")

    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "plan": plan,
    }

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils.logger import logger
from app.services.llm_study import generate_study_plan
from app.services.notifier import notify_admin

router = APIRouter()

class GenerateRequest(BaseModel):
    file_id: str
    days: int
    language: str

@router.post("/")
async def generate_plan(request: GenerateRequest):
    file_id = request.file_id
    days = request.days
    language = request.language

    logger.info(f"[GENERATE] Start → file_id='{file_id}' days={days} language='{language}'")

    try:
        text = generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
        )

        if not text:
            raise ValueError("Empty response from LLM")

        logger.info(f"[GENERATE] Completed → {len(text)} chars")

        return {
            "status": "ok",
            "file_id": file_id,
            "days": days,
            "language": language,
            "text": text,
        }

    except Exception as e:
        logger.exception(f"[GENERATE] ERROR: {e}")
        await notify_admin(f"❌ GENERATE FAILED\nfile_id={file_id}\n{e}")
        raise HTTPException(status_code=500, detail=str(e))

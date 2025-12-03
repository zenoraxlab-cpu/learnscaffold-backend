from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.utils.logger import logger

from app.services.generator_prompt import build_prompt
from app.services.openai_client import run_chat_completion
from app.services.notifier import notify_admin

from app.config import UPLOAD_DIR

import os
import json

router = APIRouter()


class GenerateRequest(BaseModel):
    file_id: str
    days: int
    language: Optional[str] = None   # en by default


@router.post("/")
async def generate_plan(payload: GenerateRequest):

    logger.info(f"[GENERATE] Start → {payload}")

    gen_language = payload.language or "en"

    analysis_path = os.path.join(UPLOAD_DIR, f"{payload.file_id}_analysis.json")

    if not os.path.exists(analysis_path):
        await notify_admin(f"❌ ERROR: Analysis file missing for {payload.file_id}")
        raise HTTPException(status_code=404, detail="Analysis file not found")

    with open(analysis_path, "r", encoding="utf-8") as f:
        analysis_data = json.load(f)

    prompt_messages = build_prompt(
        analysis=analysis_data,
        days=payload.days,
        language=gen_language
    )

    try:
        result_text = await run_chat_completion(prompt_messages)
    except Exception as e:
        await notify_admin(f"❌ OpenAI generation failed for {payload.file_id}\n{e}")
        raise HTTPException(status_code=500, detail="LLM generation failed")

    output_path = os.path.join(UPLOAD_DIR, f"{payload.file_id}_plan.json")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result_text)

    logger.info("[GENERATE] Successfully completed")

    return {
        "status": "ok",
        "file_id": payload.file_id,
        "language": gen_language,
        "days": payload.days
    }

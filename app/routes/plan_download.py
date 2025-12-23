from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

from app.config import UPLOAD_DIR

router = APIRouter()

@router.get("/{task_id}")
def download_plan(task_id: str):
    path = os.path.join(UPLOAD_DIR, f"{task_id}_final.json")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Study plan not found")

    return FileResponse(
        path,
        media_type="application/json",
        filename=f"study_plan_{task_id}.json"
    )

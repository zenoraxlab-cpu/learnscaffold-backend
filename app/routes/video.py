from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def process_video():
    return {"status": "ok", "message": "Video endpoint working"}

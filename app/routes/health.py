from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health():
    return {"status": "ok", "message": "AI StudyPlan Generator backend is running"}

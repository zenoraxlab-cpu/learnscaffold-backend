from io import BytesIO
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
import os
import json

from app.services.mwp_export import build_mwp_plan_pdf
from app.config import UPLOAD_DIR

router = APIRouter()

# --- ШРИФТ (оставляем как было) ---
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"
pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


@router.post("/pdf")
def generate_plan_pdf(payload: dict = Body(...)):
    task_id = payload.get("task_id")
    if not task_id:
        raise HTTPException(400, detail="task_id is required")

    final_path = os.path.join(UPLOAD_DIR, f"{task_id}_final.json")

    if not os.path.exists(final_path):
        raise HTTPException(404, detail="AI plan not ready")

    with open(final_path, encoding="utf-8") as f:
        final_data = json.load(f)

    ai_plan = final_data.get("ai_plan")
    if not ai_plan:
        raise HTTPException(500, detail="ai_plan missing in final.json")

    # === MWP: AI PLAN → TEXT → PDF ===
    content, pdf_bytes = build_mwp_plan_pdf(
        ai_plan,
        pdf_title="Учебный план по дням"
    )

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="study-plan.pdf"'
        },
    )

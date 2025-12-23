import json
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.config import UPLOAD_DIR

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"

FONT_NAME = "DejaVuSans"
FONT_SIZE = 11

pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


@router.get("/pdf/{task_id}")
def download_plan_pdf(task_id: str):
    final_path = Path(UPLOAD_DIR) / f"{task_id}_final.json"

    if not final_path.exists():
        raise HTTPException(status_code=404, detail="Plan not found")

    with open(final_path, encoding="utf-8") as f:
        data = json.load(f)

    structure = data.get("structure", [])

    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    text = pdf.beginText(40, height - 50)
    text.setFont(FONT_NAME, FONT_SIZE)

    for item in structure:
        title = item.get("title", "")
        pages = item.get("pages", [])

        line = f"{title} (pages {', '.join(map(str, pages))})"

        if text.getY() < 60:
            pdf.drawText(text)
            pdf.showPage()
            text = pdf.beginText(40, height - 50)
            text.setFont(FONT_NAME, FONT_SIZE)

        text.textLine(line)
        text.textLine("")

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    buf.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="study-plan-{task_id}.pdf"'
    }

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers=headers,
    )

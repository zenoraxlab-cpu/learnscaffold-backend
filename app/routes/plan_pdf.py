from io import BytesIO
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"

FONT_NAME = "DejaVuSans"
FONT_SIZE = 11

pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


@router.post("/pdf")
def generate_plan_pdf(payload: dict = Body(...)):
    content = payload.get("content")

    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=400, detail="content is required")

    buf = BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    text = pdf.beginText(40, height - 50)
    text.setFont(FONT_NAME, FONT_SIZE)

    for line in content.splitlines():
        if text.getY() < 60:
            pdf.drawText(text)
            pdf.showPage()
            text = pdf.beginText(40, height - 50)
            text.setFont(FONT_NAME, FONT_SIZE)

        text.textLine(line)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()

    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="study-plan.pdf"'
        },
    )

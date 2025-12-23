from io import BytesIO
from pathlib import Path
from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.schemas.studyplan import PlanPdfRequest

router = APIRouter()

# ---------------------------------------------------------
# FONT (cyrillic)
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"

FONT_NAME = "DejaVuSans"
FONT_SIZE = 11

pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def wrap_line(line: str, max_width: float) -> List[str]:
    if not line:
        return [""]

    words = line.split(" ")
    res: List[str] = []
    current = ""

    for w in words:
        candidate = (current + " " + w).strip()
        width = pdfmetrics.stringWidth(candidate, FONT_NAME, FONT_SIZE)

        if width <= max_width:
            current = candidate
        else:
            if current:
                res.append(current)
            current = w

    if current:
        res.append(current)

    return res


@router.post("/pdf")
async def generate_plan_pdf(payload: PlanPdfRequest):
    buf = BytesIO()

    pdf = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    left_margin = 40
    right_margin = 40
    top_margin = 50
    bottom_margin = 60

    max_text_width = page_width - left_margin - right_margin

    text = pdf.beginText(left_margin, page_height - top_margin)
    text.setFont(FONT_NAME, FONT_SIZE)

    for raw_line in payload.content.splitlines():
        for line in wrap_line(raw_line, max_text_width):
            if text.getY() < bottom_margin:
                pdf.drawText(text)
                pdf.showPage()
                text = pdf.beginText(left_margin, page_height - top_margin)
                text.setFont(FONT_NAME, FONT_SIZE)

            text.textLine(line)

    pdf.drawText(text)
    pdf.showPage()
    pdf.save()
    buf.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="study-plan-{payload.days}-days.pdf"'
    }

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers=headers,
    )

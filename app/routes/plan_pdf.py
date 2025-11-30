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
# Регистрация шрифта с поддержкой кириллицы
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # папка app/
FONT_PATH = BASE_DIR / "fonts" / "DejaVuSans.ttf"

FONT_NAME = "DejaVuSans"
FONT_SIZE = 11

pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_PATH)))


def wrap_line(line: str, max_width: float) -> List[str]:
    """
    Простой перенос строки по словам под заданную ширину (max_width в pt).
    """
    if not line:
        # пустая строка — просто перенос вниз
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
    """
    Принимает от фронтенда текст учебного плана и возвращает PDF-файл.
    """
    buf = BytesIO()

    pdf = canvas.Canvas(buf, pagesize=A4)
    page_width, page_height = A4

    # Поля
    left_margin = 40
    right_margin = 40
    top_margin = 50
    bottom_margin = 60

    max_text_width = page_width - left_margin - right_margin

    text_object = pdf.beginText(left_margin, page_height - top_margin)
    text_object.setFont(FONT_NAME, FONT_SIZE)

    for raw_line in payload.content.splitlines():
        # заворачиваем строку по ширине
        for line in wrap_line(raw_line, max_text_width):
            # новая страница, если ушли за нижнее поле
            if text_object.getY() < bottom_margin:
                pdf.drawText(text_object)
                pdf.showPage()
                text_object = pdf.beginText(left_margin, page_height - top_margin)
                text_object.setFont(FONT_NAME, FONT_SIZE)

            text_object.textLine(line)

    pdf.drawText(text_object)
    pdf.showPage()
    pdf.save()
    buf.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="study-plan-{payload.days}-days.pdf"'
    }

    return StreamingResponse(buf, media_type="application/pdf", headers=headers)

from __future__ import annotations

import os
from io import BytesIO
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


def _register_font(font_path: str) -> str:
    font_name = "DejaVuSans"
    if font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font_name, font_path))
    return font_name


def text_to_pdf_bytes(text: str, title: Optional[str] = None) -> bytes:
    """
    Minimal, predictable PDF renderer:
    - Unicode-safe (Cyrillic OK)
    - automatic page breaks
    - single-column layout
    """

    # === ПРАВИЛЬНЫЙ ПУТЬ К ШРИФТУ ===
    font_path = os.path.join("app", "fonts", "DejaVuSans.ttf")

    if os.path.exists(font_path):
        font_name = _register_font(font_path)
    else:
        # fallback — PDF создастся, но кириллица сломается
        font_name = "Helvetica"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    left = 48
    top = height - 56
    line_h = 14
    y = top

    # --- основной шрифт ---
    c.setFont(font_name, 12)

    # --- заголовок ---
    if title:
        c.setFont(font_name, 14)
        c.drawString(left, y, title)
        y -= (line_h * 2)
        c.setFont(font_name, 12)

    # --- текст ---
    for line in text.splitlines():
        if y < 56:
            c.showPage()
            c.setFont(font_name, 12)
            y = top

        c.drawString(left, y, line)
        y -= line_h

    c.showPage()
    c.save()

    return buf.getvalue()

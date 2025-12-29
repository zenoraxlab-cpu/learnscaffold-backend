# app/services/mwp_export.py
from __future__ import annotations

from typing import Any, Tuple

from app.services.mwp_plan_formatter import format_mwp_text
from app.services.mwp_pdf_renderer import text_to_pdf_bytes


def build_mwp_plan_pdf(ai_plan: Any, pdf_title: str = "Учебный план") -> Tuple[str, bytes]:
    """
    Returns:
      - mwp_text (strict format)
      - pdf_bytes (ready to return to client)
    """
    mwp_text = format_mwp_text(ai_plan)
    pdf_bytes = text_to_pdf_bytes(mwp_text, title=pdf_title)
    return mwp_text, pdf_bytes

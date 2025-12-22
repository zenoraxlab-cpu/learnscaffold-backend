# app/services/pdf_text.py

import asyncio
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text


async def extract_clean_text(path: str) -> str:
    """
    Возвращает ПОЛНЫЙ очищенный текст.
    Без asyncio.run().
    Работает корректно внутри FastAPI.
    """

    logger.info(f"[PDF_TEXT] extract_clean_text: {path}")

    try:
        # extract_pdf_text может быть async или sync — обрабатываем оба случая
        if asyncio.iscoroutinefunction(extract_pdf_text):
            text = await extract_pdf_text(path)
        else:
            text = await asyncio.to_thread(extract_pdf_text, path)

        if not text:
            logger.warning("[PDF_TEXT] Empty text after extraction.")
            return ""

        return text

    except Exception as e:
        logger.error(f"[PDF_TEXT] Failed: {e}")
        return ""

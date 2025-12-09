import fitz
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text


def extract_clean_text(path: str) -> list:
    """
    Возвращает текст по страницам:
    [
        { "page": 1, "text": "..." },
        ...
    ]
    """
    logger.info(f"[PDF_TEXT] extract_clean_text: {path}")
    try:
        text = ""

        # Извлечение текста (OCR fallback внутри)
        text = asyncio.run(extract_pdf_text(path))
        if not text:
            logger.warning("[PDF_TEXT] Empty text after extraction.")
            return []

        doc = fitz.open(path)
        page_count = len(doc)
        doc.close()

        # Простое деление текста по количеству страниц
        chunk_size = max(1, len(text) // page_count)
        result = []

        for i in range(page_count):
            start = i * chunk_size
            end = (i + 1) * chunk_size
            result.append({
                "page": i + 1,
                "text": text[start:end].strip()
            })

        return result

    except Exception as e:
        logger.error(f"[PDF_TEXT] Failed: {e}")
        return []

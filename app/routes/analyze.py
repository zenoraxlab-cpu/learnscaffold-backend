from fastapi import APIRouter, HTTPException
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.structure_extractor import extract_structure
from app.config import UPLOAD_DIR
import os

router = APIRouter()


@router.post("/")
async def analyze_document(file_id: str):
    """
    Анализ документа:
    1) Поиск файла
    2) Извлечение текста (с fallback на постраничный текст)
    3) Очистка текста
    4) Извлечение страниц
    5) Нарезка на чанки
    6) LLM-классификация
    7) Извлечение структуры (главы, подглавы, страницы)
    """

    logger.info(f"[ANALYZE] request: file_id={file_id}")

    # ---------------------------------------------------------------
    # 1. Находим файл
    # ---------------------------------------------------------------
    file_path = None
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path:
        raise HTTPException(status_code=404, detail=f"File with id={file_id} not found")

    logger.info(f"[ANALYZE] Found file for analysis: {file_path}")

    # ---------------------------------------------------------------
    # 2. Извлекаем текст + страницы, делаем fallback
    # ---------------------------------------------------------------
    # 2.1. Пытаемся извлечь страницы (для ссылок и возможного fallback)
    try:
        pages = extract_pdf_pages(file_path)
        logger.info(f"[ANALYZE] Extracted {len(pages)} pages (per-page)")
    except Exception:
        logger.exception("[ANALYZE] Failed to extract PDF pages")
        pages = []

    # 2.2. Пытаемся извлечь «сплошной» текст
    raw_text = extract_pdf_text(file_path)
    if not raw_text or not raw_text.strip():
        logger.warning("[ANALYZE] extract_pdf_text returned empty, using pages text as fallback")

        # если есть pages — склеиваем текст по страницам
        if pages:
            joined = []
            for p in pages:
                # p может быть dict или str, зависит от реализации extract_pdf_pages
                if isinstance(p, dict):
                    joined.append(str(p.get("text", "")))
                else:
                    joined.append(str(p))
            raw_text = "\n\n".join(joined)

    if not raw_text or not raw_text.strip():
        logger.error("[ANALYZE] Failed to extract any text from document (even via pages)")
        raise HTTPException(status_code=500, detail="Failed to extract text from PDF")

    # ---------------------------------------------------------------
    # 3. Очищаем текст
    # ---------------------------------------------------------------
    cleaned_text = clean_text(raw_text)
    if not cleaned_text.strip():
        raise HTTPException(status_code=500, detail="Text cleaning produced empty result")

    # ---------------------------------------------------------------
    # 4. Делаем чанки (для классификации)
    # ---------------------------------------------------------------
    chunks = chunk_text(cleaned_text, max_chars=2000, overlap=200)
    if not chunks:
        raise HTTPException(status_code=500, detail="Chunking failed")

    # ---------------------------------------------------------------
    # 5. LLM-классификация (определение типа документа)
    # ---------------------------------------------------------------
    analysis = classify_document(chunks[0])
    logger.info(f"[ANALYZE] LLM classification: {analysis}")

    # ---------------------------------------------------------------
    # 6. Извлекаем структуру PDF только по file_path
    # ---------------------------------------------------------------
    structure = extract_structure(file_path) or []
    logger.info(f"[ANALYZE] Structure extraction: {len(structure)} sections")

    # ---------------------------------------------------------------
    # 7. Базовая аналитика по тексту
    # ---------------------------------------------------------------
    total_length = len(cleaned_text)
    chunks_count = len(chunks)
    avg_chunk_size = total_length // chunks_count if chunks_count else 0
    preview = chunks[0][:1000]

    logger.info(
        f"[ANALYZE] completed: length={total_length}, chunks={chunks_count}, pages={len(pages)}"
    )

    return {
        "status": "ok",
        "file_id": file_id,
        "total_length": total_length,
        "chunks_count": chunks_count,
        "avg_chunk_size": avg_chunk_size,
        "pages": len(pages),
        "first_chunk_preview": preview,
        "analysis": analysis,
        "structure": structure,
    }

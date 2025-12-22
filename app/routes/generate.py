import os
from fastapi import APIRouter, HTTPException
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_pages
from app.services.page_chunker import chunk_pages
from app.services.llm_study import generate_units_from_chunk
from app.config import UPLOAD_DIR

router = APIRouter()

@router.post("")  # ← ВАЖНО: пустой путь, т.к. prefix="/generate"
async def generate(payload: dict):
    logger.info("[GENERATE] Start plan generation")

    file_id = payload.get("file_id")  # это task_id из /analyze/init
    days = int(payload.get("days", 10))
    language = payload.get("language", "ru")

    if not file_id:
        raise HTTPException(status_code=422, detail="file_id required")

    pdf_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    # 1. Извлекаем текст постранично
    pages = extract_pdf_pages(pdf_path)
    pages = [p for p in pages if p.get("text", "").strip()]

    if not pages:
        raise HTTPException(status_code=500, detail="No text extracted from PDF")

    # 2. Чанкаем
    chunks = chunk_pages(pages)
    logger.info(f"[GENERATE] Chunks created: {len(chunks)}")

    # 3. Генерируем учебные юниты
    all_units = []

    for chunk in chunks:
        logger.info(
            f"[GENERATE] Pages {chunk['page_start']}–{chunk['page_end']}"
        )

        result = await generate_units_from_chunk(
            text=chunk["text"],
            page_start=chunk["page_start"],
            page_end=chunk["page_end"],
            language=language,
        )

        for unit in result.get("units", []):
            unit["source_pages"] = list(
                range(chunk["page_start"], chunk["page_end"] + 1)
            )

        all_units.extend(result.get("units", []))

    if not all_units:
        raise HTTPException(status_code=500, detail="Failed to generate units")

    # 4. Группируем по дням
    units_per_day = max(1, len(all_units) // days)
    plan = []

    for d in range(1, days + 1):
        start = (d - 1) * units_per_day
        end = d * units_per_day if d < days else len(all_units)
        day_units = all_units[start:end]

        covered_pages = sorted(
            {p for u in day_units for p in u.get("source_pages", [])}
        )

        plan.append({
            "day_number": d,
            "title": f"День {d}" if language == "ru" else f"Day {d}",
            "page_range": (
                f"{covered_pages[0]}-{covered_pages[-1]}"
                if covered_pages else ""
            ),
            "units": day_units,
        })

    logger.info("[GENERATE] Plan generation completed")

    return {
        "status": "ok",
        "file_id": file_id,
        "total_units": len(all_units),
        "total_chunks": len(chunks),
        "plan": plan,
    }

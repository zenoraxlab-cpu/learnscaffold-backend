from typing import List
from fastapi import APIRouter, HTTPException
import os

from app.utils.logger import logger
from app.services.pdf_extractor import (
    extract_pdf_text,
    extract_pdf_pages,
)
from app.services.structure_extractor import extract_structure
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.llm_study import generate_day_plan
from app.services.llm_flashcards import generate_flashcards_for_lesson
from app.config import UPLOAD_DIR

router = APIRouter()


# ---------------------------------------------------------------------
# Build text context for flashcards
# ---------------------------------------------------------------------
def build_lesson_context(lesson: dict) -> str:
    parts: list[str] = []

    title = lesson.get("title")
    if title:
        parts.append(f"Title: {title}")

    theory = lesson.get("theory")
    if theory:
        parts.append(
            "Theory:\n" + (theory if isinstance(theory, str) else "\n".join(theory))
        )

    practice = lesson.get("practice")
    if practice:
        parts.append("Practice:\n" + "\n".join(f"- {p}" for p in practice))

    summary = lesson.get("summary")
    if summary:
        parts.append(
            "Summary:\n" + (summary if isinstance(summary, str) else "\n".join(summary))
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------
# Add source_pages to each lesson
# ---------------------------------------------------------------------
def attach_page_links(plan_days: List[dict], pages_count: int) -> List[dict]:
    total_days = len(plan_days)
    if total_days == 0 or pages_count <= 0:
        return plan_days

    pages_per_day = max(1, pages_count // total_days)

    for i, lesson in enumerate(plan_days):
        if lesson.get("source_pages"):
            continue

        start = i * pages_per_day + 1
        end = pages_count if i == total_days - 1 else start + pages_per_day - 1
        end = min(end, pages_count)

        lesson["source_pages"] = list(range(start, end + 1))

    return plan_days


# ---------------------------------------------------------------------
# MAIN ENDPOINT
# ---------------------------------------------------------------------
@router.post("/study")
async def generate_study_plan(
    file_id: str,
    days: int = 14,
    include_flashcards: bool = False,
    flashcards_per_lesson: int = 5,
):
    logger.info(
        f"[GENERATE] Request: file_id={file_id}, days={days}, "
        f"flashcards={include_flashcards}"
    )

    # -----------------------------------------------------------------
    # 1. Resolve file path
    # -----------------------------------------------------------------
    file_path = None
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    # -----------------------------------------------------------------
    # 2. Extract structure (chapters, headings)
    # -----------------------------------------------------------------
    structure = extract_structure(file_path) or []

    # -----------------------------------------------------------------
    # 3. Count PDF pages
    # -----------------------------------------------------------------
    try:
        pages = await extract_pdf_pages(file_path)
        pages_count = len(pages)
    except Exception as e:
        logger.error(f"[GENERATE] Page extraction failed: {e}")
        pages_count = 0

    # -----------------------------------------------------------------
    # 4. Extract text — with Google OCR fallback inside
    # -----------------------------------------------------------------
    raw_text = await extract_pdf_text(file_path)

    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=500, detail="Failed to extract text from PDF")

    # -----------------------------------------------------------------
    # 5. Clean text
    # -----------------------------------------------------------------
    cleaned = clean_text(raw_text)

    # -----------------------------------------------------------------
    # 6. Split into chunks
    # -----------------------------------------------------------------
    chunks = chunk_text(cleaned, max_chars=2500, overlap=200)
    if not chunks:
        raise HTTPException(status_code=500, detail="Chunking failed")

    # -----------------------------------------------------------------
    # 7. Classification
    # -----------------------------------------------------------------
    analysis = classify_document(chunks[0])

    # -----------------------------------------------------------------
    # 8. Generate daily lessons
    # -----------------------------------------------------------------
    plan_days: List[dict] = []

    for day in range(1, days + 1):
        lesson = generate_day_plan(
            day_number=day,
            total_days=days,
            document_type=analysis.get("document_type"),
            main_topics=analysis.get("main_topics", []),
            summary=analysis.get("summary", ""),
            structure=structure,
        )

        # Add flashcards if requested
        if include_flashcards:
            ctx = build_lesson_context(lesson)
            if ctx.strip():
                lesson["flashcards"] = generate_flashcards_for_lesson(
                    content=ctx,
                    language=analysis.get("language", "en"),
                    count=flashcards_per_lesson,
                )

        plan_days.append(lesson)

    # -----------------------------------------------------------------
    # 9. Map lessons → PDF pages
    # -----------------------------------------------------------------
    plan_days = attach_page_links(plan_days, pages_count)

    logger.info("[GENERATE] Completed OK")

    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": analysis,
        "structure": structure,
        "plan": {"days": plan_days},
    }

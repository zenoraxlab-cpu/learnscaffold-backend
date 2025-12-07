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
from app.services.llm_study import generate_study_plan
from app.services.llm_flashcards import generate_flashcards_for_lesson
from app.config import UPLOAD_DIR

router = APIRouter()


# ---------------------------------------------------------------------
# Helper: build text context for flashcards
# ---------------------------------------------------------------------
def build_lesson_context(lesson: dict) -> str:
    parts: list[str] = []

    title = lesson.get("title")
    if title:
        parts.append(f"Title: {title}")

    theory = lesson.get("theory")
    if theory:
        parts.append("Theory:\n" + (theory if isinstance(theory, str) else "\n".join(theory)))

    practice = lesson.get("practice")
    if practice:
        parts.append("Practice:\n" + "\n".join(f"- {p}" for p in practice))

    summary = lesson.get("summary")
    if summary:
        parts.append("Summary:\n" + (summary if isinstance(summary, str) else "\n".join(summary)))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------
# NEW: Smart matching lessons → PDF pages
# ---------------------------------------------------------------------
def attach_source_pages(plan_days: List[dict], structure: List[dict]) -> List[dict]:
    """
    Привязка страниц PDF к урокам по смыслу.
    Мы делаем максимально простой, но надёжный fuzzy matching:
    - сравнение по подстроке
    - сравнение по ключевым словам (разбиваем на токены)
    """

    # preprocess structure topics
    indexed = []
    for block in structure:
        topic = block.get("topic")
        page = block.get("page")

        if not topic or not page:
            continue

        indexed.append({
            "topic": topic.lower(),
            "tokens": set(topic.lower().replace(",", " ").replace(";", " ").split()),
            "page": page
        })

    for lesson in plan_days:
        title = (lesson.get("title") or "").lower()
        title_tokens = set(title.replace(",", " ").replace(";", " ").split())

        matched_pages = []

        for item in indexed:
            topic = item["topic"]

            # direct substring match
            if topic in title or title in topic:
                matched_pages.append(item["page"])
                continue

            # token intersection
            if len(title_tokens.intersection(item["tokens"])) >= 2:
                matched_pages.append(item["page"])

        # assign result
        lesson["source_pages"] = sorted(set(matched_pages))

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
    logger.info(f"[GENERATE] Request: file_id={file_id}, days={days}, flashcards={include_flashcards}")

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
    # 2. Extract structure
    # -----------------------------------------------------------------
    structure = extract_structure(file_path) or []
    logger.warning(f"STRUCTURE DEBUG: {structure}")

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
    # 4. Extract text
    # -----------------------------------------------------------------
    raw_text = await extract_pdf_text(file_path)
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=500, detail="Failed to extract text from PDF")

    cleaned = clean_text(raw_text)

    # -----------------------------------------------------------------
    # 5. Chunking
    # -----------------------------------------------------------------
    chunks = chunk_text(cleaned, max_chars=2500, overlap=200)
    if not chunks:
        raise HTTPException(status_code=500, detail="Chunking failed")

    # -----------------------------------------------------------------
    # 6. Classification
    # -----------------------------------------------------------------
    analysis = classify_document(chunks[0])

    # -----------------------------------------------------------------
    # 7. Generate lessons (LLM)
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

        if include_flashcards:
            ctx = build_lesson_context(lesson)
            if ctx.strip():
                lesson["flashcards"] = generate_flashcards_for_lesson(
                    content=ctx,
                    language=analysis.get("language", "en"),
                    count=flashcards_per_lesson,
                )

        plan_days.append(lesson)

    logger.warning(f"LESSON TITLES DEBUG: {[d.get('title') for d in plan_days]}")

    # -----------------------------------------------------------------
    # 8. Attach pages
    # -----------------------------------------------------------------
    plan_days = attach_source_pages(plan_days, structure)
    logger.warning(f"PAGES ATTACHED DEBUG: {[d.get('source_pages') for d in plan_days]}")

    # -----------------------------------------------------------------
    # RETURN (with debug fields)
    # -----------------------------------------------------------------
    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": analysis,
        "structure": structure,
        "plan": {"days": plan_days},

        # ===== DEBUG FIELDS (удалим после теста) =====
        "debug_structure": structure,
        "debug_titles": [d.get("title") for d in plan_days],
        "debug_pages_attached": [d.get("source_pages") for d in plan_days],
    }

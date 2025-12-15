from fastapi import APIRouter, HTTPException
from typing import List
import os

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.structure_extractor import extract_structure
from app.services.text_cleaner import clean_text
from app.services.classifier import classify_document
from app.services.llm_study import generate_study_plan as llm_generate_study_plan
from app.services.llm_flashcards import generate_flashcards_for_lesson
from app.config import UPLOAD_DIR

router = APIRouter()

# ... (attach_source_pages и build_lesson_context без изменений) ...

@router.post("/study")
async def generate_study(
    file_id: str,
    days: int = 14,
    language: str = "en",
    include_flashcards: bool = False,
    flashcards_per_lesson: int = 5,
):
    logger.info(f"[GENERATE] Request: file_id={file_id}, days={days}, language={language}, flashcards={include_flashcards}")

    # Resolve file path
    file_path = None
    for fname in os.listdir(UPLOAD_DIR):
        if fname.startswith(file_id):
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")

    # Extract structure
    structure = extract_structure(file_path) or []

    # Page count
    try:
        pages = await extract_pdf_pages(file_path)
        pages_count = len(pages)
    except Exception as e:
        logger.error(f"[GENERATE] Page extraction failed: {e}")
        pages_count = 0

    # Extract and clean text
    raw_text = await extract_pdf_text(file_path)
    if not raw_text or not raw_text.strip():
        raise HTTPException(status_code=500, detail="Failed to extract text from PDF")

    cleaned = clean_text(raw_text)

    # Chunking
 
    # Classification
    classification = classify_document(chunks[0])
    summary = classification.get("summary", "")
    document_language = classification.get("language", "en")

    # === GENERATE STUDY PLAN ===
    try:
        result = await llm_generate_study_plan(
            file_id=file_id,
            days=days,
            language=language,
            summary=summary,
            structure=structure,
            document_language=document_language,
        )

        plan_days = result.get("plan", [])

    except Exception as e:
        logger.error(f"[GENERATE] LLM study plan failed: {e}")
        raise HTTPException(status_code=500, detail="Study plan generation failed")

    # FLASHCARDS (optional)
    if include_flashcards:
        for lesson in plan_days:
            ctx = build_lesson_context(lesson)
            if ctx.strip():
                try:
                    lesson["flashcards"] = generate_flashcards_for_lesson(
                        content=ctx,
                        language=language,
                        count=flashcards_per_lesson,
                    )
                except Exception as e:
                    logger.warning(f"[FLASHCARDS] Failed for lesson {lesson.get('title')}: {e}")

    # Attach pages
    plan_days = attach_source_pages(plan_days, structure)

    return {
        "status": "ok",
        "file_id": file_id,
        "days": days,
        "analysis": classification,
        "structure": structure,
        "plan": {"days": plan_days},
    }

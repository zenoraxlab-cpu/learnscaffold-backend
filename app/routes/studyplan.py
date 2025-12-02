from typing import List

from fastapi import APIRouter, HTTPException

from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_text, extract_pdf_pages
from app.services.structure_extractor import extract_structure
from app.services.text_cleaner import clean_text
from app.services.chunker import chunk_text
from app.services.classifier import classify_document
from app.services.llm_study import generate_day_plan
from app.services.llm_flashcards import generate_flashcards_for_lesson
from app.config import UPLOAD_DIR
import os

router = APIRouter()


def build_lesson_context(lesson: dict) -> str:
  """
  Build a concatenated text context for a single lesson
  to be used for flashcard generation.

  It carefully handles strings and lists for fields like
  theory, practice, and summary.
  """
  parts: list[str] = []

  title = lesson.get("title")
  if title:
      parts.append(f"Title: {title}")

  theory = lesson.get("theory")
  if theory:
      if isinstance(theory, list):
          theory_text = "\n".join(str(t) for t in theory)
      else:
          theory_text = str(theory)
      parts.append("Theory:\n" + theory_text)

  practice = lesson.get("practice")
  if practice:
      if isinstance(practice, list):
          practice_text = "\n".join(f"- {str(p)}" for p in practice)
      else:
          practice_text = str(practice)
      parts.append("Practice:\n" + practice_text)

  summary = lesson.get("summary")
  if summary:
      if isinstance(summary, list):
          summary_text = "\n".join(str(s) for s in summary)
      else:
          summary_text = str(summary)
      parts.append("Summary:\n" + summary_text)

  return "\n\n".join(parts)


def attach_page_links(plan_days: List[dict], pages_count: int) -> List[dict]:
  """
  Evenly distribute original PDF pages across lessons (days).

  Example:
    100 pages, 5 days → ~20 pages per day.

  If a lesson already has source_pages (from the LLM), we keep them
  and do not overwrite.
  """
  total_days = len(plan_days)
  if total_days == 0 or pages_count <= 0:
      return plan_days

  pages_per_day = max(1, pages_count // total_days)

  for i, lesson in enumerate(plan_days):
      # Skip if LLM already provided explicit page mapping
      if lesson.get("source_pages"):
          continue

      start = i * pages_per_day + 1
      if i == total_days - 1:
          # Last day takes the remaining tail
          end = pages_count
      else:
          end = min(pages_count, start + pages_per_day - 1)

      lesson["source_pages"] = list(range(start, end + 1))

  return plan_days


@router.post("/study")
async def generate_study_plan(
  file_id: str,
  days: int = 14,
  include_flashcards: bool = False,
  flashcards_per_lesson: int = 5,
):
  """
  Study Mode plan generation.

  Pipeline:
    1) Locate uploaded file by file_id
    2) Extract full structure (chapters + pages)
    3) Extract raw text from PDF
    4) Clean and chunk text
    5) Classify document with LLM
    6) Generate a day-by-day learning plan for `days`
    7) Optionally generate flashcards for each day
  """

  logger.info(
      "[GENERATE] Study plan request: "
      f"file_id={file_id}, days={days}, "
      f"include_flashcards={include_flashcards}, "
      f"flashcards_per_lesson={flashcards_per_lesson}"
  )

  # -----------------------------------------------------------
  # 1. Locate file by file_id
  # -----------------------------------------------------------
  file_path = None
  for fname in os.listdir(UPLOAD_DIR):
      if fname.startswith(file_id):
          file_path = os.path.join(UPLOAD_DIR, fname)
          break

  if not file_path:
      raise HTTPException(status_code=404, detail="File not found")

  # -----------------------------------------------------------
  # 2. Extract document structure (chapters + pages)
  # -----------------------------------------------------------
  structure = extract_structure(file_path)
  if not structure:
      logger.warning(
          "[GENERATE] Structure extraction returned empty result, "
          "falling back to text-only pipeline"
      )
      structure = []

  # -----------------------------------------------------------
  # 2.1. Count PDF pages for later linking
  # -----------------------------------------------------------
  try:
      pages = extract_pdf_pages(file_path)
      pages_count = len(pages)
      logger.info(f"[GENERATE] PDF pages detected: {pages_count}")
  except Exception as e:
      logger.error(f"[GENERATE] Failed to extract pages: {e}")
      pages_count = 0

  # -----------------------------------------------------------
  # 3. Extract and clean text
  # -----------------------------------------------------------
  raw_text = extract_pdf_text(file_path)
  cleaned = clean_text(raw_text)

  chunks = chunk_text(cleaned, max_chars=2500, overlap=200)
  if not chunks:
      raise HTTPException(status_code=500, detail="Failed to chunk text")

  # -----------------------------------------------------------
  # 4. LLM-based classification using the first chunk
  # -----------------------------------------------------------
  analysis = classify_document(chunks[0])

  # -----------------------------------------------------------
  # 5. Generate day-by-day plan (+ optional flashcards)
  # -----------------------------------------------------------
  plan: List[dict] = []
  for day in range(1, days + 1):
      lesson = generate_day_plan(
          day_number=day,
          total_days=days,
          document_type=analysis.get("document_type"),
          main_topics=analysis.get("main_topics", []),
          summary=analysis.get("summary", ""),
          structure=structure,
      )

      # 5.1. Generate flashcards for this lesson (optional)
      if include_flashcards:
          content = build_lesson_context(lesson)
          if content.strip():
              lesson["flashcards"] = generate_flashcards_for_lesson(
                  content=content,
                  language=analysis.get("language", "en"),
                  count=flashcards_per_lesson,
              )

      plan.append(lesson)

  # -----------------------------------------------------------
  # 6. Attach original PDF page references to each lesson
  # -----------------------------------------------------------
  plan = attach_page_links(plan, pages_count)

  logger.info("[GENERATE] Study plan generated successfully")

  return {
      "status": "ok",
      "file_id": file_id,
      "days": days,
      "analysis": analysis,
      "structure": structure,
      "plan": {"days": plan},
  }

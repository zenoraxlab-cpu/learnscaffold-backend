from typing import List, Dict, Any
import json

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL
from app.utils.logger import logger


"""
llm_study.py

Responsibilities:
– Safe LLM call (Responses API)
– Build prompts for daily lessons
– Parse JSON with protection
"""


# --------------------------------------------------------------
# Init OpenAI client (explicit)
# --------------------------------------------------------------
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


# --------------------------------------------------------------
# Base LLM caller using Responses API
# --------------------------------------------------------------
def call_llm(prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    Safe LLM call using OpenAI Responses API.

    Always returns *string* (may be empty).
    Never throws errors to FastAPI layer.
    """
    try:
        logger.info("[LLM_STUDY] Calling LLM...")

        resp = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": "You are an expert study planner. Always return JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            max_output_tokens=900,
            temperature=0.4,
        )

        # Unified safe accessor
        output = resp.output_text or ""
        return output.strip()

    except Exception as e:
        logger.error(f"[LLM_STUDY] LLM call failed: {e}")
        return ""


# --------------------------------------------------------------
# Build prompt for one day lesson
# --------------------------------------------------------------
def _build_day_prompt(
    day_number: int,
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> str:

    topics_text = ", ".join(main_topics) if main_topics else "Unknown topics"

    # Build TOC preview
    if structure:
        toc_lines = []
        for ch in structure:
            title = ch.get("title") or ch.get("name") or ""
            if not title:
                continue

            page = ch.get("page") or ch.get("start_page")
            line = f"- p.{page}: {title}" if page else f"- {title}"
            toc_lines.append(line)

        structure_text = "\n".join(toc_lines) if toc_lines else "No explicit structure."
    else:
        structure_text = "No explicit structure."

    return f"""
Create a detailed study lesson for DAY {day_number} of {total_days}.

TEXTBOOK INFO:
- Document type: {document_type}
- Main topics: {topics_text}

SHORT SUMMARY:
{summary}

TABLE OF CONTENTS:
{structure_text}

TASK:
Return STRICT JSON for DAY {day_number}:

{{
  "day_number": {day_number},
  "title": "Short lesson title",
  "goals": ["Goal 1", "Goal 2"],
  "theory": "Explanation of the concepts learned today.",
  "practice": ["Task 1", "Task 2"],
  "summary": "Short wrap-up of the day.",
  "quiz": [
    {{ "q": "Question 1", "a": "Answer 1" }},
    {{ "q": "Question 2", "a": "Answer 2" }}
  ]
}}

RULES:
- The content MUST relate only to DAY {day_number}.
- No markdown. No comments.
- Only valid JSON.
"""


# --------------------------------------------------------------
# Parse JSON with fallback
# --------------------------------------------------------------
def _parse_day_plan(raw: str, day_number: int) -> Dict[str, Any]:
    """
    Converts raw JSON from LLM into a normalized lesson dict.
    On any error — returns safe empty placeholder.
    """
    try:
        if not raw.strip():
            raise ValueError("Empty LLM output")

        data = json.loads(raw)

        if not isinstance(data, dict):
            raise ValueError("Expected JSON object")

        result = {
            "day_number": data.get("day_number", day_number),
            "title": data.get("title") or f"Day {day_number}",
            "goals": data.get("goals") or [],
            "theory": data.get("theory") or "",
            "practice": data.get("practice") or [],
            "summary": data.get("summary") or "",
            "quiz": data.get("quiz") or [],
        }

        # normalize lists
        if not isinstance(result["goals"], list):
            result["goals"] = [str(result["goals"])]

        if not isinstance(result["practice"], list):
            result["practice"] = [str(result["practice"])]

        # normalize quiz items
        quiz_ok = []
        for q in result["quiz"]:
            if isinstance(q, dict):
                qq = (q.get("q") or "").strip()
                aa = (q.get("a") or "").strip()
                if qq and aa:
                    quiz_ok.append({"q": qq, "a": aa})
        result["quiz"] = quiz_ok

        return result

    except Exception as e:
        logger.error(f"[LLM_STUDY] Failed to parse JSON: {e}")

        return {
            "day_number": day_number,
            "title": f"Day {day_number}",
            "goals": [],
            "theory": "",
            "practice": [],
            "summary": "",
            "quiz": [],
        }


# --------------------------------------------------------------
# Public function — generate full day lesson
# --------------------------------------------------------------
def generate_day_plan(
    day_number: int,
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:

    prompt = _build_day_prompt(
        day_number=day_number,
        total_days=total_days,
        document_type=document_type,
        main_topics=main_topics,
        summary=summary,
        structure=structure,
    )

    raw = call_llm(prompt)
    return _parse_day_plan(raw, day_number=day_number)

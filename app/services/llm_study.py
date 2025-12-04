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
– Parse JSON safely
– Generate full study plan
"""

# --------------------------------------------------------------
# Init OpenAI client
# --------------------------------------------------------------
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)

# --------------------------------------------------------------
# Base LLM caller (Responses API)
# --------------------------------------------------------------
def call_llm(prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    Safe LLM call that never throws errors.
    Always returns string.
    """

    try:
        logger.info("[LLM_STUDY] Calling LLM...")

        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": "You are an expert study planner. Always return JSON only."},
                {"role": "user", "content": prompt},
            ],
            max_output_tokens=900,
            temperature=0.4,
        )

        out = resp.output_text or ""
        return out.strip()

    except Exception as e:
        logger.error(f"[LLM_STUDY] LLM call failed: {e}")
        return ""

# --------------------------------------------------------------
# Build prompt for one lesson
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

    # Table of contents
    if structure:
        toc = []
        for ch in structure:
            title = ch.get("title") or ch.get("name") or ""
            if not title:
                continue

            page = ch.get("page") or ch.get("start_page")
            line = f"- p.{page}: {title}" if page else f"- {title}"
            toc.append(line)

        toc_text = "\n".join(toc) if toc else "No explicit structure."
    else:
        toc_text = "No explicit structure."

    return f"""
Create a detailed study lesson for DAY {day_number} of {total_days}.

TEXTBOOK INFO:
- Document type: {document_type}
- Main topics: {topics_text}

SHORT SUMMARY:
{summary}

TABLE OF CONTENTS:
{toc_text}

TASK:
Return STRICT JSON for DAY {day_number}:

{{
  "day_number": {day_number},
  "title": "Short lesson title",
  "goals": ["Goal 1", "Goal 2"],
  "theory": "Explanation.",
  "practice": ["Task 1", "Task 2"],
  "summary": "Wrap-up.",
  "quiz": [
    {{ "q": "Question 1", "a": "Answer 1" }},
    {{ "q": "Question 2", "a": "Answer 2" }}
  ]
}}

RULES:
- No markdown.
- No explanations outside JSON.
- Valid JSON only.
"""

# --------------------------------------------------------------
# Parse JSON safely
# --------------------------------------------------------------
def _parse_day_plan(raw: str, day_number: int) -> Dict[str, Any]:
    try:
        if not raw.strip():
            raise ValueError("Empty response")

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

        # Normalize lists
        if not isinstance(result["goals"], list):
            result["goals"] = [str(result["goals"])]

        if not isinstance(result["practice"], list):
            result["practice"] = [str(result["practice"])]

        # Normalize quiz
        quiz_clean = []
        for q in result["quiz"]:
            if isinstance(q, dict):
                qq = (q.get("q") or "").strip()
                aa = (q.get("a") or "").strip()
                if qq and aa:
                    quiz_clean.append({"q": qq, "a": aa})
        result["quiz"] = quiz_clean

        return result

    except Exception as e:
        logger.error(f"[LLM_STUDY] JSON parse error: {e}")
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
# Public — generate one day lesson
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
    return _parse_day_plan(raw, day_number)

# --------------------------------------------------------------
# Public — generate plan for N days
# --------------------------------------------------------------
def generate_study_plan(
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:

    logger.info(f"[LLM_STUDY] Generating full plan for {total_days} days...")

    plan: List[Dict[str, Any]] = []

    for day in range(1, total_days + 1):
        try:
            lesson = generate_day_plan(
                day_number=day,
                total_days=total_days,
                document_type=document_type,
                main_topics=main_topics,
                summary=summary,
                structure=structure,
            )
            plan.append(lesson)

        except Exception as e:
            logger.error(f"[LLM_STUDY] Failed to generate day {day}: {e}")

            plan.append({
                "day_number": day,
                "title": f"Day {day}",
                "goals": [],
                "theory": "",
                "practice": [],
                "summary": "",
                "quiz": [],
            })

    logger.info(f"[LLM_STUDY] Plan generated: {len(plan)} days")
    return plan

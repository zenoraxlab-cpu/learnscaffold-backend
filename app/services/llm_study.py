import os
import json
from typing import List, Dict, Any

from openai import OpenAI
from app.utils.logger import logger

"""
llm_study.py

Задача:
– общий вызов LLM (call_llm) с безопасным try/except
– генерация плана на ОДИН день (generate_day_plan)
"""

_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_llm(prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    Базовый вызов LLM.
    При любой ошибке логируем и возвращаем пустую строку,
    чтобы не ронять весь API.
    """
    try:
        logger.info("[LLM_STUDY] Calling LLM")
        resp = _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert study planner and teacher."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        content = resp.choices[0].message.content or ""
        return content
    except Exception as e:
        logger.error(f"[LLM_STUDY] LLM call failed: {e}")
        return ""


def _build_day_prompt(
    day_number: int,
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> str:
    topics_text = ", ".join(main_topics) if main_topics else "Unknown topics"

    if structure:
        toc_lines = []
        for ch in structure:
            title = ch.get("title") or ch.get("name") or ""
            page = ch.get("page") or ch.get("start_page") or ""
            if title:
                if page:
                    toc_lines.append(f"- p.{page}: {title}")
                else:
                    toc_lines.append(f"- {title}")
        structure_text = "\n".join(toc_lines) if toc_lines else "No explicit chapter structure."
    else:
        structure_text = "No explicit chapter structure."

    return f"""
You are designing a detailed study plan for a textbook.

Today is DAY {day_number} out of {total_days} days.

TEXTBOOK INFO:
- Document type: {document_type}
- Main topics: {topics_text}

SHORT SUMMARY OF THE TEXTBOOK:
{summary}

TABLE OF CONTENTS / STRUCTURE (if available):
{structure_text}

TASK:
Create a detailed lesson plan for this specific day (DAY {day_number}) that moves the learner through the material in a logical sequence over {total_days} total days.

The lesson for this day MUST be returned as a JSON object with the following structure:

{{
  "day_number": {day_number},
  "title": "Short title for the day",
  "goals": [
    "Goal 1",
    "Goal 2"
  ],
  "theory": "Concise but meaningful explanation of what to learn today.",
  "practice": [
    "Practical task 1",
    "Practical task 2"
  ],
  "summary": "Short wrap-up of the day.",
  "quiz": [
    {{"q": "Question 1", "a": "Answer 1"}},
    {{"q": "Question 2", "a": "Answer 2"}}
  ]
}}

REQUIREMENTS:
- Focus only on what is relevant for DAY {day_number}, assuming there will be {total_days} total days.
- Goals and practice tasks should be concrete and actionable.
- Quiz questions should check understanding of key concepts for this day.
- Return ONLY valid JSON. No extra comments, no markdown.
"""


def _parse_day_plan(raw: str, day_number: int) -> Dict[str, Any]:
    """
    Парсим JSON от модели.
    Если что-то пошло не так — возвращаем минимальный skeleton, чтобы API не падал.
    """
    try:
        if not raw.strip():
            raise ValueError("Empty LLM response")

        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Day plan must be a JSON object")

        result: Dict[str, Any] = {
            "day_number": data.get("day_number", day_number),
            "title": data.get("title") or f"Day {day_number}",
            "goals": data.get("goals") or [],
            "theory": data.get("theory") or "",
            "practice": data.get("practice") or [],
            "summary": data.get("summary") or "",
            "quiz": data.get("quiz") or [],
        }

        if not isinstance(result["practice"], list):
            result["practice"] = [str(result["practice"])]
        else:
            result["practice"] = [str(x) for x in result["practice"]]

        if not isinstance(result["goals"], list):
            result["goals"] = [str(result["goals"])]
        else:
            result["goals"] = [str(x) for x in result["goals"]]

        quiz_norm = []
        for item in result["quiz"]:
            if not isinstance(item, dict):
                continue
            q = (item.get("q") or "").strip()
            a = (item.get("a") or "").strip()
            if q and a:
                quiz_norm.append({"q": q, "a": a})
        result["quiz"] = quiz_norm

        return result

    except Exception as e:
        logger.error(f"[LLM_STUDY] Failed to parse day plan JSON: {e}")
        return {
            "day_number": day_number,
            "title": f"Day {day_number}",
            "goals": [],
            "theory": "",
            "practice": [],
            "summary": "",
            "quiz": [],
        }


def generate_day_plan(
    day_number: int,
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Публичная функция, которую вызывает /generate/study.
    """
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

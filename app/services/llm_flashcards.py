from typing import List, Dict
import json

from app.services.llm_study import call_llm


"""
llm_flashcards.py

Flashcard generator for lessons.
Uses the unified LLM caller from llm_study.py (Responses API).
"""


# -------------------------------------------------------------------
# Prompt builder
# -------------------------------------------------------------------
def build_flashcards_prompt(content: str, language: str, count: int) -> str:
    """
    Build a strict JSON-only flashcard generation prompt.
    """
    return f"""
You are an educational assistant.

Generate EXACTLY {count} flashcards in language "{language}".

Each flashcard MUST have the structure:
{{ "q": "...", "a": "..." }}

Rules:
- Output MUST be ONLY JSON.
- No markdown.
- No comments.
- No explanations before or after JSON.
- Questions must be short and precise.
- Answers must be correct and clear.
- Cover the key ideas from the content.

Return ONLY a JSON array like:
[
  {{ "q": "What is X?", "a": "X is ..." }},
  {{ "q": "Why does Y happen?", "a": "Because ..." }}
]

CONTENT:
\"\"\"{content}\"\"\"
"""


# -------------------------------------------------------------------
# JSON parser
# -------------------------------------------------------------------
def parse_flashcards_json(raw: str) -> List[Dict]:
    """
    Parse a JSON array of flashcards.
    Returns [] if the response is invalid.
    """
    try:
        if not raw or not raw.strip():
            raise ValueError("Empty LLM response")

        data = json.loads(raw)

        if not isinstance(data, list):
            raise ValueError("Expected a JSON array")

        flashcards: List[Dict] = []

        for item in data:
            if not isinstance(item, dict):
                continue

            q = (item.get("q") or "").strip()
            a = (item.get("a") or "").strip()

            if q and a:
                flashcards.append({"q": q, "a": a})

        return flashcards

    except Exception as e:
        print(f"[FLASHCARDS] Failed to parse JSON: {e}")
        return []


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
def generate_flashcards_for_lesson(
    content: str,
    language: str = "en",
    count: int = 5,
) -> List[Dict]:
    """
    Generate flashcards for a lesson using the unified LLM caller.
    """
    if not content.strip():
        return []

    prompt = build_flashcards_prompt(content, language, count)

    try:
        raw = call_llm(prompt)
    except Exception as e:
        print(f"[FLASHCARDS] LLM call failed: {e}")
        return []

    if not raw:
        return []

    return parse_flashcards_json(raw)

from typing import List, Dict
import json

"""
Сервис для генерации обучающих карточек (flashcards).
"""

try:
    from app.services.llm_study import call_llm  # используем общий LLM-хелпер
except Exception:
    # На всякий случай: если import не удался, определим заглушку.
    def call_llm(prompt: str, model: str = "gpt-4.1-mini") -> str:  # type: ignore
        print("[flashcards] call_llm fallback: no LLM available")
        return ""


def build_flashcards_prompt(content: str, language: str, count: int) -> str:
    return f"""
You are a study assistant.

Generate {count} flashcards for spaced repetition based on the content below.

Requirements:
- Language: {language}
- Each card MUST have "q" and "a".
- Questions should be concise and specific.
- Answers should be clear and correct.
- Cover key concepts and typical exam-style questions.

Return JSON array ONLY, no explanations:
[
  {{ "q": "Question 1", "a": "Answer 1" }},
  ...
]

Content:
\"\"\"{content}\"\"\"
"""


def parse_flashcards_json(raw: str) -> List[Dict]:
    try:
        if not raw.strip():
            raise ValueError("Empty LLM response for flashcards")

        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError("Flashcards must be a list")

        result: List[Dict] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            q = (item.get("q") or "").strip()
            a = (item.get("a") or "").strip()
            if q and a:
                result.append({"q": q, "a": a})

        return result

    except Exception as e:
        print("[flashcards] parse error:", e)
        return []


def generate_flashcards_for_lesson(
    content: str,
    language: str = "en",
    count: int = 5,
) -> List[Dict]:
    if not content.strip():
        return []

    prompt = build_flashcards_prompt(content=content, language=language, count=count)
    try:
        raw = call_llm(prompt)
    except Exception as e:
        print("[flashcards] LLM call failed:", e)
        return []

    if not raw:
        return []

    return parse_flashcards_json(raw)

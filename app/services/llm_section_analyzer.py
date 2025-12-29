import json
from typing import Dict

from app.services.openai_client import run_chat_completion


SYSTEM_PROMPT = (
    "You are a university teaching assistant helping students study independently."
)


async def analyze_section_with_llm(
    title: str,
    text: str,
) -> Dict:
    """
    Analyze ONE semantic section using OpenAI.
    Returns dict with topics, learning_goals, difficulty.
    """

    user_prompt = f"""
You are given ONE section of academic material.

Section title:
{title}

Section text (excerpt):
{text}

Your task is to analyze the educational content of this section.

Respond STRICTLY in valid JSON, without explanations or extra text:

{{
  "topics": [
    "2–4 concrete topics actually covered in this section"
  ],
  "learning_goals": [
    "2–3 learning outcomes phrased as: 'The student should be able to...'"
  ],
  "difficulty": "easy | medium | hard"
}}

Rules:
- Do NOT invent topics that are not present in the text
- Avoid vague phrases like 'introduction', 'overview', 'basics'
- If the section is introductory in nature, set difficulty = easy
""".strip()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw = await run_chat_completion(
        messages=messages,
        model="gpt-4.1-mini",
    )

    try:
        data = json.loads(raw)
        return {
            "topics": data.get("topics", []),
            "learning_goals": data.get("learning_goals", []),
            "difficulty": data.get("difficulty", "medium"),
        }
    except Exception:
        # Fallback — пайплайн не должен падать
        return {
            "topics": [],
            "learning_goals": [],
            "difficulty": "medium",
        }

import json
from app.utils.logger import logger
from app.services.openai_client import client


async def generate_study_plan(file_id: str, days: int, language: str, summary: str, structure: list):
    """
    Generate a structured study plan using the selected target language.
    The model MUST respond ONLY in the target language.
    """

    logger.info(f"[LLM_STUDY] Generating study plan for {days} days in '{language}'...")

    system_prompt = f"""
You are an AI assistant that generates structured study plans.

THE MOST IMPORTANT RULE:
---------------------------------------------------------
You MUST ALWAYS produce the output in the target language specified below,
even if the original document is in another language.
Never mix languages. Never write anything in the original language unless
it matches the target language exactly.
---------------------------------------------------------

TARGET LANGUAGE: {language}

STRUCTURE REQUIREMENTS:
- Return a JSON object with:
  {{
    "status": "ok",
    "days": <int>,
    "plan": [
        {{
          "day_number": <int>,
          "title": "<string>",
          "goals": ["<string>", ...],
          "theory": "<string>",
          "practice": ["<string>", ...],
          "summary": "<string>",
          "quiz": [
            {{ "q": "<string>", "a": "<string>" }},
            ...
          ]
        }},
        ...
    ]
  }}

- No markdown formatting.
- No explanations.
- No comments.
- Only valid JSON.
"""

    user_prompt = f"""
Document summary:
{summary}

Extracted structure (sections list):
{json.dumps(structure, ensure_ascii=False)}

Generate a {days}-day study program.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.2,
            max_tokens=6000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        logger.info(f"[LLM_STUDY] Raw JSON response: {raw[:200]}...")

        data = json.loads(raw)

        if "plan" not in data or "days" not in data:
            raise ValueError("Invalid plan JSON structure")

        return data

    except Exception as e:
        logger.error("[LLM_STUDY] LLM generation failed")
        logger.exception(e)
        raise

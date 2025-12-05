import json
from app.utils.logger import logger
from app.services.openai_client import client


async def generate_study_plan(
    file_id: str,
    days: int,
    language: str,
    summary: str,
    structure: list,
    document_language: str
):
    """
    Generate a structured study plan using the selected target language.
    The model MUST respond ONLY in the target language.
    """

    logger.warning(f"[DEBUG LLM] Target language = '{language}', document_language = '{document_language}'")
    logger.info(f"[LLM_STUDY] Generating study plan for {days} days in '{language}'...")

    system_prompt = f"""
You are an AI assistant that generates structured study plans.

CRITICAL LANGUAGE RULE:
---------------------------------------------------------
You MUST ALWAYS produce the ENTIRE output strictly in the TARGET LANGUAGE.
IGNORE the language of the document, summary, and structure.
NEVER output text in the original document's language unless
TARGET LANGUAGE equals that language.

TARGET LANGUAGE: {language}
ORIGINAL DOCUMENT LANGUAGE: {document_language}

ABSOLUTE PROHIBITIONS:
- Do NOT mirror the language of the summary.
- Do NOT output Russian unless TARGET LANGUAGE == "ru".
- Do NOT mix languages.
- Rewrite EVERYTHING in the target language as if originally written in it.

OUTPUT FORMAT (STRICT):
Return ONLY valid JSON:
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
         {{"q": "<string>", "a": "<string>"}}
      ]
    }}
  ]
}}

NO markdown.
NO comments.
NO explanations.
Only the JSON object.
"""

    user_prompt = f"""
Here is the document summary (use meaning ONLY, do NOT copy its language):
{summary}

Extracted structure (sections list):
{json.dumps(structure, ensure_ascii=False)}

Generate a {days}-day structured study program.
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
        logger.info(f"[LLM_STUDY] Raw JSON response (first 200 chars): {raw[:200]}")

        data = json.loads(raw)

        if "plan" not in data or "days" not in data:
            raise ValueError("Invalid plan JSON structure")

        return data

    except Exception as e:
        logger.error("[LLM_STUDY] LLM generation failed")
        logger.exception(e)
        raise


# ----------------------------------------------------------------------
# Flashcards compatibility wrapper
# ----------------------------------------------------------------------
async def call_llm(prompt: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error("[LLM_STUDY] call_llm failed")
        logger.exception(e)
        raise

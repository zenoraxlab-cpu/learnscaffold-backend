# app/services/generator_prompt.py

LANG_MAP = {
    "en": "English",
    "ru": "Russian",
    "es": "Spanish",
    "de": "German",
    "fr": "French"
}

def build_prompt(analysis: dict, days: int, language: str):
    """
    Create structured prompt for generating the study plan.
    The study plan must ALWAYS be generated in the selected language.
    """

    lang_name = LANG_MAP.get(language, "English")

    system_message = f"""
You are an AI that generates structured study plans.
You MUST respond strictly in {lang_name}.
Do NOT translate to any other language.
Do NOT detect language. The output language is explicitly chosen by the user.
Your job is only to generate a detailed, high-quality study program.
"""

    # Summary of contents user uploaded
    analysis_summary = analysis.get("analysis", {})
    structure_summary = analysis.get("structure", [])
    file_description = analysis_summary.get("short_description", "")

    user_message = f"""
Generate a {days}-day study plan using ONLY the following extracted data:

CONTENT SUMMARY:
{analysis_summary}

STRUCTURE (chapters, sections):
{structure_summary}

DOCUMENT DESCRIPTION:
{file_description}

Rules:
- Write everything in {lang_name}.
- Each day must include: goals, theory, practice, summary.
- Return clean JSON with a list "days": [...]
"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user",    "content": user_message.strip()}
    ]

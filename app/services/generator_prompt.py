def build_prompt(analysis: dict, days: int, language: str):
    """
    Build prompt for studyplan generation.
    By default everything is generated in English.
    """

    lang_map = {
        "en": "English",
        "ru": "Russian",
        "es": "Spanish",
        "de": "German",
        "fr": "French"
    }

    target_language = lang_map.get(language, "English")

    system_message = f"""
You are an AI that generates structured study plans.

MANDATORY RULES:
- The study plan MUST be written strictly in {target_language}.
- Do NOT translate into any other language.
- Output must be clean, structured JSON.

"""

    user_message = f"""
Generate a {days}-day study plan based on the following document analysis:

{analysis}

Your output must contain exactly {days} lessons.
Use consistent structure: title, goals, theory, practice, summary, review questions.
"""

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]

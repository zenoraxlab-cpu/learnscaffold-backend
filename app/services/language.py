from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a language detector.
Respond ONLY with the language name in English
(e.g. "Russian", "English", "German", "Spanish").
"""

def detect_language(text: str) -> str:
    text = (text or "")[:4000]

    if not text.strip():
        return "en"

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=3,
        )

        raw = resp.choices[0].message.content.lower()

        if "russian" in raw or "рус" in raw:
            return "ru"
        if "english" in raw or "англ" in raw:
            return "en"
        if "german" in raw:
            return "de"
        if "spanish" in raw:
            return "es"

        return "en"

    except:
        return "en"

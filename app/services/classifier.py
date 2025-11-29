import openai
import json
import re
from app.utils.logger import logger


def cleanup_json(text: str) -> str:
    """
    Удаляет ```json ... ``` блоки, лишние бэктики, Markdown-форматирование.
    Оставляет чистый JSON.
    """
    # Удаляем тройные кавычки ```json ... ```
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```", "", text)

    # Убираем лишние пробелы по краям
    return text.strip()


def classify_document(chunk: str) -> dict:
    logger.info("LLM classification started")

    prompt = f"""
Проанализируй текст и верни строго JSON.

Текст:
\"\"\"{chunk[:4000]}\"\"\"

Формат ответа строго такой:

{{
  "document_type": "...",
  "main_topics": ["...", "..."],
  "level": "beginner | intermediate | advanced",
  "summary": "...",
  "recommended_days": 0
}}

Отвечай только JSON, без комментариев.
"""

    response = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are an expert education analyst. Return only JSON."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=800,
    )

    raw_output = response.choices[0].message.content

    logger.info(f"LLM raw output: {raw_output[:200]}")

    cleaned = cleanup_json(raw_output)

    try:
        result = json.loads(cleaned)
    except Exception as e:
        logger.error(f"JSON parsing failed after cleanup: {e}")
        logger.error(f"CLEANED JSON:\n{cleaned}")
        raise ValueError(f"Failed to parse cleaned JSON: {cleaned}")

    logger.info("LLM classification completed")
    return result

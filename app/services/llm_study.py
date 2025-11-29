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

    return text.strip()


def generate_study_plan(chunks, analysis, days: int, focus_topics=None):
    """
    Auto-Mode generator.
    Берёт:
      - чанки текста
      - анализ документа
      - количество дней
      - фокусные темы (опционально)
    Генерирует:
      - учебный план по дням
    """

    logger.info(f"Study plan generation started: days={days}")

    # Собираем основу контекста
    base_context = f"""
Документ: {analysis.get("document_type")}
Темы: {", ".join(analysis.get("main_topics", []))}
Уровень материала: {analysis.get("level")}
Краткое описание: {analysis.get("summary")}

Чанк материала (фрагмент):
\"\"\"{chunks[0][:3000]}\"\"\"
"""

    if focus_topics:
        base_context += f"\nФокусные темы пользователя: {', '.join(focus_topics)}\n"

    prompt = f"""
На основе следующей информации создай структурированный учебный курс на {days} дней.

Правила:
1. Режим Auto — стиль выбирай сам (теория/практика/квизы/проекты).
2. Каждый день должен иметь структуру:
   {{
     "day": 1,
     "title": "...",
     "topics": ["...", "..."],
     "theory": "...",
     "practice": "...",
     "quiz": ["вопрос 1", "вопрос 2"],
     "summary": "..."
   }}
3. Отвечай строго JSON списком:
   {{
     "days": [ ... ]
   }}

Контекст:
{base_context}
"""

    response = openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "Ты эксперт-методолог. Отвечай строго JSON."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=6000
    )

    raw_output = response.choices[0].message.content
    logger.info(f"Study LLM raw output: {raw_output[:200]}")

    cleaned = cleanup_json(raw_output)

    try:
        result = json.loads(cleaned)
    except Exception as e:
        logger.error(f"JSON parsing failed in study generator: {e}")
        logger.error(f"CLEANED:\n{cleaned}")
        raise ValueError(f"Failed to parse study JSON: {cleaned}")

    logger.info("Study plan generation complete")
    return result

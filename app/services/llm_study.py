import json
from app.utils.logger import logger
from app.services.openai_client import client


# ===================================================================
# НОВАЯ ФУНКЦИЯ — генерация единиц из реального текста
# ===================================================================
async def generate_units_from_chunk(
    text: str,
    page_start: int,
    page_end: int,
    language: str = "ru"
) -> dict:
    lang_names = {
        "ru": "русском",
        "en": "английском",
        "es": "испанском",
        "de": "немецком",
        "fr": "французском"
    }
    lang_name = lang_names.get(language, "русском")

    prompt = f"""
Ты — профессиональный педагог.

На основе текста ниже (страницы {page_start}–{page_end}) создай от 1 до 4 учебных единиц.

Текст:
--- НАЧАЛО ТЕКСТА ---
{text[:11500]}
--- КОНЕЦ ТЕКСТА ---

Выведи СТРОГО JSON на {lang_name} языке:
{{
  "units": [
    {{
      "title": "Название темы",
      "goals": ["цель 1", "цель 2"],
      "theory_summary": "Краткое изложение",
      "practice": ["задание 1", "задание 2"],
      "quiz": [{{"q": "Вопрос?", "a": "Ответ"}}]
    }}
  ]
}}
Только JSON.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        if "units" not in data:
            return {"units": []}
        return data
    except Exception as e:
        logger.error(f"[LLM_UNITS] Ошибка: {e}")
        return {"units": []}


# ===================================================================
# СТАРАЯ ФУНКЦИЯ — ОСТАВЛЕНА ДЛЯ СОВМЕСТИМОСТИ (чтобы сервер запустился)
# ===================================================================
async def generate_study_plan(
    file_id: str,
    days: int,
    language: str,
    summary: str,
    structure: list,
    document_language: str
) -> dict:
    logger.warning("[LLM_STUDY] Используется старая generate_study_plan — план неточный!")
    # Заглушка — возвращаем минимальный валидный ответ, чтобы не падало
    return {
        "status": "ok",
        "days": days,
        "plan": [
            {
                "day_number": 1,
                "title": "Введение (старая версия)",
                "goals": ["Ознакомиться с материалом"],
                "theory": "План будет заменён на новый в следующей версии",
                "practice": ["Прочитать документ"],
                "summary": "Это заглушка",
                "quiz": [{"q": "Готовы к новому плану?", "a": "Да!"}]
            }
        ]
    }


# ===================================================================
# Универсальная обертка
# ===================================================================
async def call_llm(prompt: str, temperature: float = 0.2, model: str = "gpt-4o-mini") -> str:
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("[LLM] call_llm failed")
        logger.exception(e)
        raise
import re
from app.utils.logger import logger


def normalize_whitespace(text: str) -> str:
    # заменяем \r\n, \r на \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # убираем повторяющиеся пустые строки (больше двух подряд → максимум одна)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # убираем лишние пробелы
    text = re.sub(r"[ \t]+", " ", text)
    return text


def remove_page_artifacts(text: str) -> str:
    # простые эвристики — можно усложнить позже
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()

        # выкидываем одиночные номера страниц (1–3 цифры в строке)
        if re.fullmatch(r"\d{1,3}", stripped):
            continue

        cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def clean_text(raw_text: str) -> str:
    """
    Базовая очистка текста после извлечения из PDF.
    """
    logger.info("Text cleaning started")
    if not raw_text:
        return ""

    text = raw_text

    text = normalize_whitespace(text)
    text = remove_page_artifacts(text)

    text = text.strip()
    logger.info(f"Text cleaning finished, length={len(text)}")
    return text

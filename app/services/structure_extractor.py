import re
from app.services.pdf_extractor import extract_pdf_pages
from app.utils.logger import logger


# ----------------------------------------------------
# Шаблоны поиска глав и подглав
# ----------------------------------------------------

SECTION_PATTERNS = [
    r"^\s*(Глава\s+\d+)",
    r"^\s*(Раздел\s+\d+)",
    r"^\s*(Тема\s+\d+)",
    r"^\s*(Chapter\s+\d+)",
    r"^\s*(Section\s+\d+)",
    r"^\s*(§\s*\d+)",
    r"^\s*(\d+\.\s+[A-Za-zА-Яа-я])",
    r"^\s*(\d+\.\d+\s+[A-Za-zА-Яа-я])",
]


def detect_heading(line: str):
    """
    Проверка: является ли строка заголовком?
    Возвращает:
      (уровень, текст заголовка) или (None, None)
    """
    for pattern in SECTION_PATTERNS:
        if re.match(pattern, line.strip()):
            # уровень зависит от вложенности (1., 1.1, 1.1.1)
            level = line.count('.') + line.count('§')
            return level, line.strip()

    return None, None


def extract_structure(path: str):
    """
    Главная функция.
    Возвращает список структурных элементов:

    [
      {
        "title": "Глава 1. Введение",
        "level": 1,
        "start_page": 1,
        "end_page": 3,
        "text": "...",
      },
      ...
    ]
    """

    logger.info(f"[STRUCT] extract_structure() for {path}")

    pages = extract_pdf_pages(path)
    if not pages:
        logger.error("[STRUCT] No pages extracted")
        return []

    structure = []
    current = None

    for p in pages:
        number = p["page"]
        lines = p["text"].split("\n")

        for line in lines:
            level, heading = detect_heading(line)

            if heading:
                # если была предыдущая глава — закрываем её
                if current:
                    current["end_page"] = number - 1
                    structure.append(current)

                # открываем новую
                current = {
                    "title": heading,
                    "level": level if level > 0 else 1,
                    "start_page": number,
                    "end_page": number,
                    "text": ""
                }

            else:
                if current:
                    current["text"] += line + "\n"

    # закрываем последнюю главу
    if current:
        current["end_page"] = pages[-1]["page"]
        structure.append(current)

    logger.info(f"[STRUCT] Extracted {len(structure)} structural units")
    return structure

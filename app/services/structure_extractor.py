# app/services/structure_extractor.py
import re
from app.services.pdf_extractor import extract_pdf_pages
from app.utils.logger import logger

"""
Hierarchical PDF structure extractor.
"""

SECTION_PATTERNS = [
    r"^\s*(Chapter\s+\d+)",
    r"^\s*(Section\s+\d+)",
    r"^\s*(Part\s+\d+)",
    r"^\s*(Topic\s+\d+)",
    r"^\s*(Unit\s+\d+)",
    r"^\s*(§\s*\d+)",
    r"^\s*(\d+(\.\d+){0,3})\s+[A-Za-zА-Яа-я]",
]


def detect_heading(line: str):
    cleaned = line.strip()
    if not cleaned:
        return None, None

    for pattern in SECTION_PATTERNS:
        m = re.match(pattern, cleaned)
        if m:
            number_part = m.group(1)
            # 1 → level=1, 1.1 → level=2, 1.1.1 → level=3
            if number_part and "." in number_part:
                level = number_part.count(".") + 1
            else:
                level = 1
            return level, cleaned

    return None, None


def insert_block(root: list, block: dict):
    level = block["level"]

    if level == 1:
        root.append(block)
        return

    parent_level = level - 1
    stack = root

    while True:
        last = stack[-1] if stack else None
        if not last:
            root.append(block)
            return

        if last["level"] == parent_level:
            last["children"].append(block)
            return

        stack = last["children"]


def extract_structure(path: str):
    logger.info(f"[STRUCT] extract_structure() for {path}")

    pages = extract_pdf_pages(path)
    if not pages:
        logger.error("[STRUCT] No pages extracted from PDF")
        return []

    structure = []
    last_block = None

    for p in pages:
        page_num = p["page"]
        text = p.get("text", "") or ""
        lines = text.split("\n")

        for line in lines:
            level, title = detect_heading(line)

            if title:
                # Close previous
                if last_block:
                    last_block["end_page"] = page_num - 1

                block = {
                    "title": title,
                    "level": level,
                    "start_page": page_num,
                    "end_page": page_num,
                    "children": [],
                    "text": ""
                }

                insert_block(structure, block)
                last_block = block

            else:
                if last_block:
                    last_block["text"] += line + "\n"

    if last_block:
        last_block["end_page"] = pages[-1]["page"]

    logger.info(f"[STRUCT] Extracted {len(structure)} top-level sections")
    return structure

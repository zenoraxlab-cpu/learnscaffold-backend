import re
from typing import List, Dict


SECTION_HEADER_RE = re.compile(
    r"^(chapter\s+\d+|section\s+\d+(\.\d+)*|\d+(\.\d+)+|[A-Z][A-Za-z0-9 ,:-]{5,})$",
    re.IGNORECASE,
)


def extract_semantic_sections(
    text: str,
    max_chars_per_section: int = 1500,
) -> List[Dict]:
    """
    Hybrid section extractor:
    - tries to split by headings
    - falls back to chunking by size
    """

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    sections: List[Dict] = []

    current_title = None
    current_buffer: List[str] = []

    def flush():
        if not current_buffer:
            return
        section_text = "\n".join(current_buffer)
        sections.append(
            {
                "title": current_title or "Untitled section",
                "text": section_text,
            }
        )

    for line in lines:
        if SECTION_HEADER_RE.match(line) and len(current_buffer) > 3:
            flush()
            current_buffer.clear()
            current_title = line
        else:
            current_buffer.append(line)

        if sum(len(x) for x in current_buffer) > max_chars_per_section:
            flush()
            current_buffer.clear()
            current_title = current_title

    flush()

    # Fallback: if document is tiny or badly formatted
    if not sections and text.strip():
        sections.append(
            {
                "title": "Main content",
                "text": text[:max_chars_per_section],
            }
        )

    return sections

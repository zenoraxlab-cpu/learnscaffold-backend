from typing import List
from app.utils.logger import logger


def chunk_text(
    text: str,
    max_chars: int = 2000,
    overlap: int = 200
) -> List[str]:
    """
    Простое посимвольное чанкирование с перекрытием.
    max_chars — размер одного куска.
    overlap — перекрытие между чанками, чтобы не рвать смысл.
    """
    logger.info(f"Chunking started, length={len(text)}, max_chars={max_chars}, overlap={overlap}")

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        # следующий чанк начинается чуть раньше конца текущего — для перекрытия
        start = end - overlap

    logger.info(f"Chunking finished, chunks={len(chunks)}")
    return chunks

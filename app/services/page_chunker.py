from typing import List, Dict
from app.utils.logger import logger

def chunk_pages(
    pages: List[Dict],
    max_chars: int = 4500,
    overlap_pages: int = 1
) -> List[Dict]:
    """
    Делит список страниц на чанки для LLM, сохраняя диапазон страниц.
    """
    if not pages:
        return []

    chunks = []
    current_text = ""
    current_pages = []
    current_start_page = pages[0]["page"]

    for page in pages:
        page_text = page["text"].strip() + "\n\n"
        test_text = current_text + page_text

        if len(test_text) > max_chars and current_pages:
            # Закрываем текущий чанк
            chunks.append({
                "text": current_text.strip(),
                "page_start": current_start_page,
                "page_end": current_pages[-1],
                "pages": current_pages[:]
            })

            # Оверлап — берём последнюю страницу для контекста
            overlap_text = ""
            if overlap_pages > 0 and len(current_pages) > 1:
                overlap_text = pages[current_pages.index(current_pages[-1])]["text"].strip() + "\n\n"

            current_text = overlap_text + page_text
            current_pages = [page["page"]]
            current_start_page = page["page"]
        else:
            current_text = test_text
            if not current_pages:
                current_start_page = page["page"]
            current_pages.append(page["page"])

    # Последний чанк
    if current_text.strip():
        chunks.append({
            "text": current_text.strip(),
            "page_start": current_start_page,
            "page_end": current_pages[-1],
            "pages": current_pages[:]
        })

    logger.info(f"[PAGE_CHUNKER] Создано {len(chunks)} чанков по страницам")
    return chunks
from app.utils.logger import logger
from app.services.pdf_extractor import extract_pdf_pages, extract_pdf_text_sync


def extract_clean_text(pdf_path: str) -> list:
    """
    SYNC.
    GUARANTEES:
      list[{ "page": int, "text": str }]
    """

    logger.info(f"[PDF_TEXT] extract_clean_text: {pdf_path}")

    try:
        pages = extract_pdf_pages(pdf_path)
        raw = extract_pdf_text_sync(pdf_path)

        text_by_page = []

        # CASE 1: already correct
        if isinstance(raw, list):
            for i, item in enumerate(raw, start=1):
                if isinstance(item, dict) and "text" in item:
                    text_by_page.append({
                        "page": item.get("page", i),
                        "text": item.get("text", "")
                    })
                elif isinstance(item, str):
                    text_by_page.append({
                        "page": i,
                        "text": item
                    })

        # CASE 2: dict {page: text}
        elif isinstance(raw, dict):
            for k, v in raw.items():
                try:
                    page = int(k)
                except Exception:
                    page = 1
                text_by_page.append({
                    "page": page,
                    "text": str(v)
                })

        # CASE 3: single string
        elif isinstance(raw, str):
            text_by_page.append({
                "page": 1,
                "text": raw
            })

        else:
            raise ValueError(f"Unsupported extract_pdf_text_sync output: {type(raw)}")

        # final safety filter
        text_by_page = [
            p for p in text_by_page
            if isinstance(p.get("text"), str) and p["text"].strip()
        ]

        logger.info(f"[PDF_TEXT] Text cleaning finished, pages={len(text_by_page)}")
        return text_by_page

    except Exception as e:
        logger.error(f"[PDF_TEXT] Failed: {e}")
        return []

import base64
import json
import httpx
import fitz

from app.config import GOOGLE_OCR_API_KEY
from app.utils.logger import logger

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


async def google_ocr_pdf(path: str) -> str:
    """
    Convert PDF → JPG per page → Google Vision OCR → merged text.
    Works even with heavy scanned textbooks.
    """

    if not GOOGLE_OCR_API_KEY:
        logger.error("[GOOGLE OCR] Missing GOOGLE_OCR_API_KEY")
        return ""

    try:
        doc = fitz.open(path)
        pages_text = []

        async with httpx.AsyncClient(timeout=60) as client:

            for i, page in enumerate(doc):

                # render page as image (PNG recommended)
                pix = page.get_pixmap(dpi=180)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")

                request_body = {
                    "requests": [
                        {
                            "image": {"content": img_b64},
                            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        }
                    ]
                }

                params = {"key": GOOGLE_OCR_API_KEY}

                resp = await client.post(
                    VISION_ENDPOINT,
                    params=params,
                    json=request_body,
                )

                if resp.status_code != 200:
                    logger.error(f"[GOOGLE OCR] HTTP {resp.status_code}")
                    continue

                js = resp.json()

                try:
                    text = js["responses"][0]["fullTextAnnotation"]["text"]
                except Exception:
                    text = ""

                pages_text.append(text)
                logger.info(f"[GOOGLE OCR] Page {i+1}/{len(doc)} OK, {len(text)} chars")

        doc.close()
        return "\n\n".join(pages_text)

    except Exception as e:
        logger.error(f"[GOOGLE OCR] Exception: {e}")
        return ""

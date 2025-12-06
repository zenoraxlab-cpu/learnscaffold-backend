import base64
import json
import httpx
import fitz

from app.config import GOOGLE_OCR_API_KEY
from app.utils.logger import logger

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


async def google_ocr_pdf(path: str) -> str:
    """
    High-reliability PDF OCR:
    - Converts each page to PNG (dpi=180)
    - Sends to Google Vision
    - Safely parses results
    - Never crashes on empty OCR responses
    """
    if not GOOGLE_OCR_API_KEY:
        logger.error("[GOOGLE OCR] Missing GOOGLE_OCR_API_KEY")
        return ""

    try:
        doc = fitz.open(path)
        pages_text = []

        async with httpx.AsyncClient(timeout=90) as client:

            for i, page in enumerate(doc):
                # -----------------------------------------------------
                # Render page as PNG
                # -----------------------------------------------------
                pix = page.get_pixmap(dpi=180)
                img_bytes = pix.tobytes("png")
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")

                # -----------------------------------------------------
                # Prepare OCR request
                # -----------------------------------------------------
                request_body = {
                    "requests": [
                        {
                            "image": {"content": img_b64},
                            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        }
                    ]
                }

                params = {"key": GOOGLE_OCR_API_KEY}

                # -----------------------------------------------------
                # Send OCR request
                # -----------------------------------------------------
                resp = await client.post(
                    VISION_ENDPOINT,
                    params=params,
                    json=request_body,
                )

                if resp.status_code != 200:
                    logger.error(f"[GOOGLE OCR] HTTP {resp.status_code}")
                    pages_text.append("")  # fallback
                    continue

                js = resp.json()

                # -----------------------------------------------------
                # Extract text safely
                # -----------------------------------------------------
                text = ""
                try:
                    response_block = js.get("responses", [{}])[0]
                    annotation = response_block.get("fullTextAnnotation")
                    if annotation:
                        text = annotation.get("text", "")
                except Exception as e:
                    logger.error(f"[GOOGLE OCR] Parsing failed: {e}")
                    text = ""

                logger.info(f"[GOOGLE OCR] Page {i+1}/{len(doc)} OK, {len(text)} chars")
                pages_text.append(text)

        doc.close()
        return "\n\n".join(pages_text)

    except Exception as e:
        logger.error(f"[GOOGLE OCR] Exception: {e}")
        return ""

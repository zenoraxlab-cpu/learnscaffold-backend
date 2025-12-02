import httpx
from app.config import settings

OCR_API_KEY = settings.OCR_API_KEY

async def ocr_process_pdf(pdf_bytes: bytes) -> str:
    if not OCR_API_KEY:
        raise RuntimeError("OCR_API_KEY not configured")

    url = "https://api.ocr.space/parse/image"

    files = {
        'file': ('document.pdf', pdf_bytes, 'application/pdf')
    }

    data = {
        'apikey': OCR_API_KEY,
        'language': 'eng',
        'OCREngine': 2
    }

    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(url, data=data, files=files)

    result = response.json()

    if result.get("IsErroredOnProcessing"):
        raise RuntimeError(result.get("ErrorMessage", ["Unknown OCR error"])[0])

    parsed_text = result.get("ParsedResults", [{}])[0].get("ParsedText", "")

    return parsed_text

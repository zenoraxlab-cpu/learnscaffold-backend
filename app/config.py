import os
from pathlib import Path
from dotenv import load_dotenv

# ----------------------------
# Load .env file (if exists)
# ----------------------------
load_dotenv()

# ----------------------------
# Base directories
# ----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Upload directory (PDF, EPUB, video, etc.)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed extensions
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".epub",
    ".djvu",
    ".txt",
    ".docx",
    ".rtf",
    ".mobi",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
}

# ----------------------------
# OpenAI configuration
# ----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY is not set. LLM features will not work.")

# ----------------------------
# Google Vision OCR (NEW)
# ----------------------------
GOOGLE_OCR_API_KEY = os.getenv("GOOGLE_OCR_API_KEY", "")

if not GOOGLE_OCR_API_KEY:
    print("WARNING: GOOGLE_OCR_API_KEY not set — scanned PDFs will fail")

# ----------------------------
# Other external services (placeholders)
# ----------------------------
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY", "")

# ----------------------------
# CORS Allowed Origins (REQUIRED)
# ----------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://learnscaffold.com",
    "https://www.learnscaffold.com",
    "https://learnscaffold-frontend.vercel.app",
]

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Папка для загрузок
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Разрешённые расширения (MVP)
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

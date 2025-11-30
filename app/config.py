import os

# Используем диск Render, который монтируется в /var/data
UPLOAD_DIR = "/var/data/uploads"

# Создаём директорию, если её нет
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

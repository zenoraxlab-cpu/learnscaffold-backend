import os
from pathlib import Path

# Базовая директория проекта (папка app/ лежит на уровень ниже)
BASE_DIR = Path(__file__).resolve().parent.parent

# Директория для загрузки файлов:
#   - по умолчанию: ./data в корне проекта
#   - на проде можно задать через переменную окружения UPLOAD_DIR
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data"))

# Создаём папку, если её нет
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Разрешённые расширения файлов
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

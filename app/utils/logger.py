import logging
from logging.handlers import RotatingFileHandler
import os

# Создаём директорию для логов
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Основной путь логов
LOG_FILE = os.path.join(LOG_DIR, "backend.log")

# Настройка логгера
logger = logging.getLogger("studyplan")
logger.setLevel(logging.INFO)

# Хендлер с ротацией (каждый файл до 5MB, хранить 3 файла)
handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)

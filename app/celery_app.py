import sys
import os

# 🛠 Хак для Render/Docker: фиксим ошибку 'sys.stdout.isatty'
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

from celery import Celery

# 🔗 Настройки Redis-брокера и backend-а из переменных окружения
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# ⚙️ Инициализация Celery-приложения
celery_app = Celery(
    "learnscaffold",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"]  # путь к модулю с задачами
)

# 📦 Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

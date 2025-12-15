# app/celery_app.py

from celery import Celery
import os

# Брокер и бэкенд — Redis (Render поддерживает, или используй Upstash/локальный)
# Важно: в Render добавь переменные окружения CELERY_BROKER_URL и CELERY_RESULT_BACKEND
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "learnscaffold",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"]  # Важно: указываем, где лежат таски
)

# Настройки (опционально)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
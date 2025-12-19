# app/celery_app.py

import sys
import os
from celery import Celery

# 🛠 Хак для Render/Docker: фиксим sys.stdout.isatty() ошибки
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

# Redis брокер и бэкенд
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "learnscaffold",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

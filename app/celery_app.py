# app/celery_app.py

import sys

# 🔧 FIX: Render stdout bug (StdoutFlusher has no isatty)
# Celery/Click вызывает sys.stdout.isatty(), а в Render его нет
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

from celery import Celery
import os

# Брокер и бэкенд — Redis (Upstash / Render Redis)
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "learnscaffold",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks"],  # где лежат таски
)

# Настройки Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # важно для стабильности в облаке
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys
import os

# Render compatibility
os.environ["TERM"] = "dumb"
os.environ["CLICOLOR"] = "0"
os.environ["PYTHONUNBUFFERED"] = "1"

# Гарантируем isatty
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False
if not hasattr(sys.stderr, "isatty"):
    sys.stderr.isatty = lambda: False

# ⛔ НЕ ИСПОЛЬЗУЕМ CLI
from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.worker_main([
        "worker",
        "--loglevel=INFO",
        "--pool=solo",
        "--without-gossip",
        "--without-mingle",
        "--without-heartbeat",
    ])

print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys
import os

# 🔧 ФИКС ДЛЯ RENDER / StdoutFlusher
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

if not hasattr(sys.stderr, "isatty"):
    sys.stderr.isatty = lambda: False

# ⚠️ ЗАМЕНЯЕМ ПРОЦЕСС (важно для Render)
os.execvp("celery", [
    "celery",
    "-A", "app.celery_app",
    "worker",
    "--loglevel=INFO",
    "--pool=solo"
])

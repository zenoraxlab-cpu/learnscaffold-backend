# run_worker.py
import sys
import subprocess

# 🔧 ФИКС ДЛЯ RENDER / StdoutFlusher
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

if not hasattr(sys.stderr, "isatty"):
    sys.stderr.isatty = lambda: False

# Запуск celery
subprocess.run([
    "celery",
    "-A", "app.celery_app",
    "worker",
    "--loglevel=INFO",
    "--pool=solo"
])

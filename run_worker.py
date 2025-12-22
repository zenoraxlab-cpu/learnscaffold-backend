print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys
import os

# 🔧 Render / Click / Celery compatibility fixes
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

if not hasattr(sys.stderr, "isatty"):
    sys.stderr.isatty = lambda: False

# ❗ КРИТИЧЕСКОЕ — отключаем TTY / цвета в Click
os.environ["TERM"] = "dumb"
os.environ["CLICOLOR"] = "0"
os.environ["CELERYD_FORCE_EXECV"] = "1"

# Запуск Celery без попыток работать с терминалом
os.execvp("celery", [
    "celery",
    "-A", "app.celery_app",
    "worker",
    "--loglevel=INFO",
    "--pool=solo",
    "--without-gossip",
    "--without-mingle",
    "--without-heartbeat",
    "--no-color",
])

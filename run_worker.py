print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys

# === Render StdoutFlusher fix ===
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

if not hasattr(sys.stderr, "isatty"):
    sys.stderr.isatty = lambda: False

from app.celery_app import celery_app

celery_app.worker_main([
    "worker",
    "--loglevel=INFO",
    "--pool=solo",
])

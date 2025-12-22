print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys

def ensure_isatty(stream):
    cls = stream.__class__
    if not hasattr(cls, "isatty"):
        cls.isatty = lambda self: False

# === Render StdoutFlusher fix (CORRECT) ===
ensure_isatty(sys.stdout)
ensure_isatty(sys.stderr)

from app.celery_app import celery_app

celery_app.worker_main([
    "worker",
    "--loglevel=INFO",
    "--pool=solo",
])

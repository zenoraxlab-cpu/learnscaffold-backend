print(">>> RUN_WORKER_BOOTSTRAP <<<", flush=True)

import sys
import io

# === Hard override stdout/stderr with wrappers that support .isatty() ===
class SafeStdWrapper(io.TextIOBase):
    def __init__(self, wrapped):
        self._wrapped = wrapped

    def write(self, s):
        return self._wrapped.write(s)

    def flush(self):
        return self._wrapped.flush()

    def isatty(self):
        return False

    def __getattr__(self, name):
        return getattr(self._wrapped, name)

sys.stdout = SafeStdWrapper(sys.stdout)
sys.stderr = SafeStdWrapper(sys.stderr)

from app.celery_app import celery_app

celery_app.worker_main([
    "worker",
    "--loglevel=INFO",
    "--pool=solo",
])

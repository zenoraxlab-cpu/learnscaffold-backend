import sys
import io

# Гарантированный stdout
class SafeStd(io.TextIOBase):
    def write(self, s):
        return sys.__stdout__.write(s)
    def flush(self):
        return sys.__stdout__.flush()
    def isatty(self):
        return False

sys.stdout = SafeStd()
sys.stderr = SafeStd()

print(">>> RUN_WORKER_DIRECT <<<", flush=True)

from app.celery_app import celery_app
from celery.worker.worker import Worker

worker = Worker(
    app=celery_app,
    loglevel="INFO",
    pool="solo",
)

worker.start()

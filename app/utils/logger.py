import logging
import sys

# -------------------------------------------------------------------
# Force stdout/stderr unbuffered so Render prints ALL logs
# -------------------------------------------------------------------
class StdoutFlusher:
    def write(self, message):
        sys.__stdout__.write(message)
        sys.__stdout__.flush()

    def flush(self):
        sys.__stdout__.flush()

sys.stdout = StdoutFlusher()
sys.stderr = StdoutFlusher()

# -------------------------------------------------------------------
# Logging configuration
# -------------------------------------------------------------------
logger = logging.getLogger("learnscaffold")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

handler.setFormatter(formatter)
logger.addHandler(handler)

# Avoid duplicate logs
logger.propagate = False

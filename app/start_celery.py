import sys
import subprocess

# Фикс ошибки isatty
if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

# Запускаем celery с нужными параметрами
subprocess.run([
    "celery",
    "-A", "app.celery_app",
    "worker",
    "--loglevel=info",
    "--pool=solo"
])

import sys

if not hasattr(sys.stdout, "isatty"):
    sys.stdout.isatty = lambda: False

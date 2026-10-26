"""Rotating file log. Never records typed text, only events and errors."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: Path, debug: bool = False) -> None:
    root = logging.getLogger("snaptype")
    if root.handlers:
        return
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_file, maxBytes=256_000, backupCount=2,
                                      encoding="utf-8")
    except OSError:
        handler = logging.NullHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)

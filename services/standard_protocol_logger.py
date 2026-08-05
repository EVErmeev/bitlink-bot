"""Logging for the standard-protocol functionality.

Writes to ``services/logs/standard_protocol.log`` so the compression, guard and
validation steps are auditable without hunting through the GUI console.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGS_DIR = Path(__file__).resolve().parent / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)

_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a file+console logger rooted in the feature folder."""
    logger = logging.getLogger(name)
    if getattr(logger, "_bit_init", False):
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh = RotatingFileHandler(
        _LOGS_DIR / "standard_protocol.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setFormatter(logging.Formatter(_FORMAT))
    fh.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    sh.setLevel(logging.INFO)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger._bit_init = True
    return logger
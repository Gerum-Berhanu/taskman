"""Centralized logging setup."""

import logging
from pathlib import Path

from app.core.config import settings


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"


def setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        filename=_LOG_DIR / "app.log",
        filemode="a",
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

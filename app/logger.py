"""Central logging configuration: console + rotating file."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_CONFIGURED = False


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """
    Configure root logger once with console and rotating file handlers.

    Args:
        log_dir: Directory for app.log; defaults to project_root/logs.
        level: Logging level for the root logger.

    Returns:
        The application logger named ``ai-shorts-bot``.
    """
    global _LOG_CONFIGURED
    logger = logging.getLogger("ai-shorts-bot")

    if _LOG_CONFIGURED:
        return logger

    if log_dir is None:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(level)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    logger.setLevel(level)
    _LOG_CONFIGURED = True
    logger.debug("Logging initialized; file=%s", log_file)
    return logger

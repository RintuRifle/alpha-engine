"""
Centralized logging configuration for the Quant Research Platform.

Uses RotatingFileHandler for log files (auto-rotates at 10MB) + StreamHandler
for console output. All modules should use `get_logger(__name__)` — never print().
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def _get_project_root() -> Path:
    """Resolve project root by walking up from this file's location."""
    return Path(__file__).resolve().parent.parent.parent


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Create or retrieve a named logger with file + console handlers.

    Args:
        name: Logger name (typically __name__ of the calling module).
        level: Logging level — DEBUG, INFO, WARNING, ERROR, CRITICAL.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(log_level)

        # Resolve logs directory relative to project root
        project_root = _get_project_root()
        log_dir = project_root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter(
            "%(asctime)s │ %(name)-30s │ %(levelname)-8s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Rotating file handler — 10MB per file, keep 5 backups
        file_handler = RotatingFileHandler(
            str(log_dir / "quant_platform.log"),
            maxBytes=10_485_760,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logger.addHandler(file_handler)

        # Console handler — same format for consistency
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

        # Prevent log propagation to root logger (avoids duplicates)
        logger.propagate = False

    return logger

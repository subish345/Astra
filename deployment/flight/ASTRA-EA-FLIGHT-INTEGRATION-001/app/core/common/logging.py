"""Structured logging subsystem for ASTRA-EA.

Enforces standardized component tags, clean console formatting, and structured file logging.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional


class ComponentFormatter(logging.Formatter):
    """Custom formatter providing uniform component tags and precise ISO timestamps."""

    def format(self, record: logging.LogRecord) -> str:
        component = getattr(record, "component", "SYSTEM")
        record.component_tag = f"[{component.upper()}]"
        return super().format(record)


def get_logger(component: str = "SYSTEM") -> logging.Logger:
    """Obtain a logger bound to a specific subsystem component tag.

    Args:
        component: Subsystem identifier (e.g. 'PERCEPTION', 'PROCEDURE', 'ASSURANCE').

    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(f"astra.{component.lower()}")
    logger.component = component  # type: ignore[attr-defined]
    return logger


def setup_logging(
    level: str = "INFO",
    log_file_path: Optional[str | Path] = None,
    log_to_console: bool = True,
) -> None:
    """Initialize global logging configuration for ASTRA-EA.

    Args:
        level: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file_path: Optional file destination for persistent audit logs.
        log_to_console: Whether to emit logs to stdout.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger = logging.getLogger("astra")
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers on re-initialization
    root_logger.handlers.clear()

    format_str = "%(asctime)s.%(msecs)03d | %(levelname)-7s | %(component_tag)-13s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = ComponentFormatter(fmt=format_str, datefmt=date_format)

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file_path:
        path = Path(log_file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

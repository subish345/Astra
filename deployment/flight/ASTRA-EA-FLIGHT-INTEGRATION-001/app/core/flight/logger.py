"""Flight-Like Bounded and Structured Logging for ASTRA-EA (Phase 18).

In accordance with Section 38 & 64:
- Bounded file size with automatic log rotation
- Includes mission ID, run ID, sequence number, timestamp, and severity
- Persists to flight_data/diagnostics/flight.log
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class FlightLogger:
    """Bounded, sequence-indexed flight logger (D18.18)."""

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_bytes: int = 20 * 1024 * 1024,  # 20 MB ceiling
        backup_count: int = 5,
        mission_id: str = "MISSION-ASTRA-01",
        run_id: str = "RUN-001",
    ) -> None:
        self.log_dir = log_dir or Path("flight_data/diagnostics")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "flight.log"
        self.mission_id = mission_id
        self.run_id = run_id
        self._sequence: int = 0

        # Set up logger
        self.logger = logging.getLogger("astra_flight_logger")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            handler = RotatingFileHandler(
                str(self.log_file),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_event(
        self,
        severity: str,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Emit a structured flight log entry."""
        self._sequence += 1
        import time

        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "severity": severity.upper(),
            "source": source,
            "message": message,
            "details": details or {},
        }
        json_str = json.dumps(entry)

        if severity.upper() == "CRITICAL":
            self.logger.critical(json_str)
        elif severity.upper() == "ERROR":
            self.logger.error(json_str)
        elif severity.upper() == "WARNING":
            self.logger.warning(json_str)
        else:
            self.logger.info(json_str)

        return entry

    def info(self, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.log_event("INFO", source, message, details)

    def warning(self, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.log_event("WARNING", source, message, details)

    def error(self, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.log_event("ERROR", source, message, details)

    def critical(self, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.log_event("CRITICAL", source, message, details)

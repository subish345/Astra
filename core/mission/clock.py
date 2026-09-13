"""Mission Clock abstraction for ASTRA-EA.

Provides synchronized, monotonic timing references for microsecond latency profiling,
timeout evaluation, and mission elapsed time (MET), while maintaining timezone-aware
UTC wall-clock timestamps for immutable audit records.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class MissionClock:
    """Centralized timekeeper for spacecraft experiment missions."""

    def __init__(self) -> None:
        self._start_monotonic: Optional[float] = None
        self._start_wall: Optional[datetime] = None
        self._paused_monotonic: Optional[float] = None
        self._total_paused_duration: float = 0.0

    def start(self) -> None:
        """Mark start of mission execution."""
        self._start_monotonic = time.monotonic()
        self._start_wall = datetime.now(timezone.utc)
        self._paused_monotonic = None
        self._total_paused_duration = 0.0

    def pause(self) -> None:
        """Pause mission elapsed time accumulation."""
        if self._start_monotonic is not None and self._paused_monotonic is None:
            self._paused_monotonic = time.monotonic()

    def resume(self) -> None:
        """Resume mission elapsed time accumulation."""
        if self._paused_monotonic is not None:
            pause_dur = time.monotonic() - self._paused_monotonic
            self._total_paused_duration += max(0.0, pause_dur)
            self._paused_monotonic = None

    @property
    def is_running(self) -> bool:
        return self._start_monotonic is not None and self._paused_monotonic is None

    @property
    def is_paused(self) -> bool:
        return self._paused_monotonic is not None

    def elapsed_seconds(self) -> float:
        """Return net mission elapsed time in seconds, excluding pauses."""
        if self._start_monotonic is None:
            return 0.0
        now = self._paused_monotonic if self._paused_monotonic is not None else time.monotonic()
        raw_elapsed = now - self._start_monotonic
        return max(0.0, raw_elapsed - self._total_paused_duration)

    def format_met(self) -> str:
        """Format mission elapsed time as standard spacecraft notation: T+HH:MM:SS.s."""
        total_sec = self.elapsed_seconds()
        hours = int(total_sec // 3600)
        minutes = int((total_sec % 3600) // 60)
        seconds = total_sec % 60
        return f"T+{hours:02d}:{minutes:02d}:{seconds:04.1f}"

    def monotonic(self) -> float:
        """Return raw system monotonic clock."""
        return time.monotonic()

    def utc_now(self) -> datetime:
        """Return timezone-aware current UTC datetime."""
        return datetime.now(timezone.utc)

    def get_time_metadata(self) -> Dict[str, Any]:
        """Return serializable temporal snapshot for telemetry and reporting."""
        return {
            "start_wall_utc": self._start_wall.isoformat() if self._start_wall else None,
            "start_monotonic": self._start_monotonic,
            "current_wall_utc": self.utc_now().isoformat(),
            "elapsed_seconds": round(self.elapsed_seconds(), 3),
            "met_string": self.format_met(),
            "total_paused_seconds": round(self._total_paused_duration, 3),
        }

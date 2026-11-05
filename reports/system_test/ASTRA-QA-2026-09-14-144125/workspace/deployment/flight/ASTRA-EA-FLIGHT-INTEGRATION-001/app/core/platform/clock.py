"""Mission Clock and Spacecraft Timing Interface Abstraction for ASTRA-EA (Phase 18).

In accordance with Section 16 & 17:
Provides wall-clock, monotonic, mission elapsed time (MET), frame timestamps,
and event sequencing. Spacecraft time protocol interface remains TBD.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ClockSource(str, enum.Enum):
    """Timing source reference (Section 17)."""
    SYSTEM_CLOCK = "SYSTEM_CLOCK"
    MISSION_CLOCK = "MISSION_CLOCK"
    SPACECRAFT_TIME_SERVICE_TBD = "SPACECRAFT_TIME_SERVICE_TBD"
    EXTERNAL_TIME_REFERENCE_TBD = "EXTERNAL_TIME_REFERENCE_TBD"


@dataclass
class FrameTimestamp:
    frame_index: int
    monotonic_time_s: float
    met_time_s: float
    utc_iso: str


@dataclass
class EventTimestamp:
    sequence_number: int
    monotonic_time_s: float
    met_time_s: float
    utc_iso: str


class MissionClock:
    """Standard Mission Clock abstraction (D18.06)."""

    def __init__(self, clock_source: ClockSource = ClockSource.SYSTEM_CLOCK) -> None:
        self.clock_source = clock_source
        self._epoch_monotonic = time.monotonic()
        self._mission_start_monotonic: Optional[float] = None
        self._sequence_counter: int = 0
        self._external_clock_offset_ms: float = 0.0

    def start_mission(self) -> None:
        """Mark start of mission for Mission Elapsed Time (MET) calculations."""
        self._mission_start_monotonic = time.monotonic()

    def get_met_seconds(self) -> float:
        """Return Mission Elapsed Time in seconds, or 0.0 if mission has not started."""
        if self._mission_start_monotonic is None:
            return 0.0
        return round(time.monotonic() - self._mission_start_monotonic, 3)

    def now_monotonic(self) -> float:
        """High-resolution monotonic time in seconds."""
        return time.monotonic()

    def now_utc_iso(self) -> str:
        """Current wall-clock time in ISO 8601 UTC format."""
        t = time.time() + (self._external_clock_offset_ms / 1000.0)
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))

    def set_clock_offset_ms(self, offset_ms: float) -> None:
        """Synchronize with future external spacecraft time service."""
        self._external_clock_offset_ms = offset_ms

    def stamp_frame(self, frame_index: int) -> FrameTimestamp:
        """Generate synchronized timestamp for video/perception frames."""
        mono = self.now_monotonic()
        return FrameTimestamp(
            frame_index=frame_index,
            monotonic_time_s=mono,
            met_time_s=self.get_met_seconds(),
            utc_iso=self.now_utc_iso(),
        )

    def stamp_event(self) -> EventTimestamp:
        """Generate strictly increasing sequence-numbered timestamp for mission events."""
        self._sequence_counter += 1
        mono = self.now_monotonic()
        return EventTimestamp(
            sequence_number=self._sequence_counter,
            monotonic_time_s=mono,
            met_time_s=self.get_met_seconds(),
            utc_iso=self.now_utc_iso(),
        )

    def get_status(self) -> Dict[str, Any]:
        return {
            "source": self.clock_source.value,
            "met_seconds": self.get_met_seconds(),
            "sequence_count": self._sequence_counter,
            "utc_iso": self.now_utc_iso(),
            "offset_ms": self._external_clock_offset_ms,
        }

# ==============================================================================
# ASTRA-EA Connection Heartbeat & Watchdog
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Lightweight link watchdog monitoring heartbeat age and classifying link quality."""

from __future__ import annotations

import time
from enum import Enum
from typing import Tuple


class LinkQuality(str, Enum):
    """Link degradation tiers."""
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class HeartbeatWatchdog:
    """Monitors heartbeat arrival intervals and classifies link quality."""

    def __init__(
        self,
        degraded_threshold_seconds: float = 2.5,
        timeout_threshold_seconds: float = 6.0,
    ) -> None:
        self.degraded_threshold = degraded_threshold_seconds
        self.timeout_threshold = timeout_threshold_seconds
        self.last_heartbeat_time: float = 0.0

    def beat(self) -> None:
        """Register a heartbeat arrival."""
        self.last_heartbeat_time = time.time()

    def check_status(self) -> Tuple[LinkQuality, float]:
        """Evaluate current link status and return (status, seconds_since_last_beat)."""
        if self.last_heartbeat_time <= 0.0:
            return LinkQuality.OFFLINE, 999.0

        elapsed = time.time() - self.last_heartbeat_time
        if elapsed < self.degraded_threshold:
            return LinkQuality.GOOD, round(elapsed, 2)
        elif elapsed < self.timeout_threshold:
            return LinkQuality.DEGRADED, round(elapsed, 2)
        else:
            return LinkQuality.OFFLINE, round(elapsed, 2)

# ==============================================================================
# ASTRA-EA Reconnection Backoff Manager
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Exponential backoff with jitter for graceful network link reconnection."""

from __future__ import annotations

import random
import time


class BackoffManager:
    """Computes bounded exponential backoff with pseudo-random jitter."""

    def __init__(
        self,
        base_interval: float = 1.0,
        max_interval: float = 8.0,
        factor: float = 1.5,
        jitter: float = 0.25,
    ) -> None:
        self.base_interval = base_interval
        self.max_interval = max_interval
        self.factor = factor
        self.jitter = jitter
        self.attempts: int = 0

    def reset(self) -> None:
        """Reset attempt counter upon successful connection."""
        self.attempts = 0

    def next_delay(self) -> float:
        """Calculate next backoff delay in seconds."""
        delay = min(self.max_interval, self.base_interval * (self.factor ** self.attempts))
        jitter_val = random.uniform(-self.jitter, self.jitter) * delay
        self.attempts += 1
        return max(0.5, round(delay + jitter_val, 2))

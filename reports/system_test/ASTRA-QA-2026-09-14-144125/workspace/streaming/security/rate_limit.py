# ==============================================================================
# ASTRA-EA Streaming Rate Limiter
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Basic connection rate limiting and client capacity protection."""

from __future__ import annotations

import collections
import time
from typing import Dict


class ConnectionRateLimiter:
    """Tracks connection attempts per IP address to guard against socket flooding."""

    def __init__(self, max_requests_per_window: int = 60, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests_per_window
        self.window_seconds = window_seconds
        self._history: Dict[str, collections.deque[float]] = collections.defaultdict(collections.deque)

    def is_allowed(self, client_ip: str) -> bool:
        """Check if client IP is within allowable request rate."""
        now = time.time()
        q = self._history[client_ip]

        # Purge stale timestamps outside sliding window
        while q and (now - q[0] > self.window_seconds):
            q.popleft()

        if len(q) >= self.max_requests:
            return False

        q.append(now)
        return True

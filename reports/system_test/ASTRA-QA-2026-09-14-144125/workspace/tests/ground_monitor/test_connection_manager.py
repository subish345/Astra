# ==============================================================================
# ASTRA-EA Connection Watchdog & Backoff Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated tests for HeartbeatWatchdog, BackoffManager, and ConnectionManager."""

from __future__ import annotations

import time
import pytest

from streaming.connection.heartbeat import HeartbeatWatchdog, LinkQuality
from streaming.connection.reconnect import BackoffManager


def test_heartbeat_watchdog_state_transitions() -> None:
    """Verify watchdog transitions between GOOD, DEGRADED, and OFFLINE."""
    watchdog = HeartbeatWatchdog(degraded_threshold_seconds=0.3, timeout_threshold_seconds=0.8)

    # Initial state with no heartbeat registered
    q, elapsed = watchdog.check_status()
    assert q == LinkQuality.OFFLINE

    # Beat registered
    watchdog.beat()
    q, elapsed = watchdog.check_status()
    assert q == LinkQuality.GOOD
    assert elapsed < 0.2

    # Wait until degraded
    time.sleep(0.35)
    q, elapsed = watchdog.check_status()
    assert q == LinkQuality.DEGRADED

    # Wait until timeout
    time.sleep(0.5)
    q, elapsed = watchdog.check_status()
    assert q == LinkQuality.OFFLINE


def test_backoff_manager_exponential_growth_and_reset() -> None:
    """Verify bounded exponential backoff calculation and reset."""
    backoff = BackoffManager(base_interval=1.0, max_interval=6.0, factor=2.0, jitter=0.0)

    d1 = backoff.next_delay()
    d2 = backoff.next_delay()
    d3 = backoff.next_delay()
    d4 = backoff.next_delay()

    assert d1 == 1.0
    assert d2 == 2.0
    assert d3 == 4.0
    assert d4 == 6.0  # Capped at max_interval

    backoff.reset()
    assert backoff.attempts == 0
    assert backoff.next_delay() == 1.0

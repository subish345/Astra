# ==============================================================================
# ASTRA-EA Ground Connection Package
# ==============================================================================
"""Connection management, heartbeat monitoring, and reconnection backoff."""

from __future__ import annotations

from streaming.connection.heartbeat import HeartbeatWatchdog, LinkQuality
from streaming.connection.manager import ConnectionManager
from streaming.connection.reconnect import BackoffManager

__all__ = [
    "HeartbeatWatchdog",
    "LinkQuality",
    "BackoffManager",
    "ConnectionManager",
]

# ==============================================================================
# ASTRA-EA Ground Telemetry Connection Manager
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Dual-channel connection orchestrator for Ground Monitor."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional
import numpy as np

from streaming.connection.heartbeat import HeartbeatWatchdog, LinkQuality
from streaming.connection.reconnect import BackoffManager
from streaming.events.client import EventStreamClient
from streaming.events.schema import GroundEvent
from streaming.video.client import VideoStreamClient

logger = logging.getLogger("connection_manager")


class ConnectionManager:
    """Orchestrates dual-channel IP connections (Video & Events) for the Ground Monitor."""

    def __init__(
        self,
        stream_url: str = "http://127.0.0.1:8554/video",
        events_url: str = "http://127.0.0.1:8765/events",
        on_frame_callback: Optional[Callable[[np.ndarray, Dict[str, float]], None]] = None,
        on_event_callback: Optional[Callable[[GroundEvent, float], None]] = None,
        on_link_status_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.stream_url = stream_url
        self.events_url = events_url
        self.on_frame = on_frame_callback
        self.on_event = on_event_callback
        self.on_link_status = on_link_status_callback

        self.watchdog = HeartbeatWatchdog()
        self.backoff = BackoffManager()

        self._video_connected = False
        self._events_connected = False
        self._video_status_msg = "DISCONNECTED"
        self._events_status_msg = "DISCONNECTED"

        self.video_client = VideoStreamClient(
            stream_url=self.stream_url,
            on_frame_callback=self._handle_video_frame,
            on_status_callback=self._handle_video_status,
        )

        self.event_client = EventStreamClient(
            events_url=self.events_url,
            on_event_callback=self._handle_event,
            on_status_callback=self._handle_event_status,
        )

        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def connect_all(self) -> None:
        """Start both streaming channels."""
        self._running = True
        self.video_client.connect()
        self.event_client.connect()

        self._monitor_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="astra_ground_watchdog",
        )
        self._monitor_thread.start()
        logger.info("ConnectionManager initiated dual-channel connection to %s and %s", self.stream_url, self.events_url)

    def disconnect_all(self) -> None:
        """Disconnect both streaming channels."""
        self._running = False
        self.video_client.disconnect()
        self.event_client.disconnect()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.5)
        logger.info("ConnectionManager disconnected all channels.")

    def _handle_video_frame(self, frame: np.ndarray, metrics: Dict[str, float]) -> None:
        if self.on_frame:
            self.on_frame(frame, metrics)

    def _handle_video_status(self, connected: bool, message: str) -> None:
        self._video_connected = connected
        self._video_status_msg = message
        self._notify_link_status()

    def _handle_event(self, event: GroundEvent, latency_ms: float) -> None:
        self.watchdog.beat()
        if self.on_event:
            self.on_event(event, latency_ms)

    def _handle_event_status(self, connected: bool, message: str) -> None:
        self._events_connected = connected
        self._events_status_msg = message
        if connected:
            self.watchdog.beat()
            self.backoff.reset()
        self._notify_link_status()

    def _watchdog_loop(self) -> None:
        """Periodic watchdog evaluating heartbeat intervals."""
        while self._running:
            time.sleep(1.0)
            self._notify_link_status()

    def _notify_link_status(self) -> None:
        """Emit comprehensive dual-channel connection state."""
        quality, elapsed = self.watchdog.check_status()

        # Classify overall status
        if self._video_connected and self._events_connected and quality == LinkQuality.GOOD:
            overall = "ONLINE"
        elif self._video_connected or self._events_connected:
            overall = "PARTIAL"
        else:
            overall = "OFFLINE"

        status_dict = {
            "overall": overall,
            "quality": quality.value,
            "video_connected": self._video_connected,
            "video_status": self._video_status_msg,
            "events_connected": self._events_connected,
            "events_status": self._events_status_msg,
            "heartbeat_age_seconds": elapsed,
            "reconnect_count": self.video_client.reconnect_count + self.event_client.reconnect_count,
            "stream_fps": self.video_client.stream_fps,
        }

        if self.on_link_status:
            try:
                self.on_link_status(status_dict)
            except Exception as exc:
                logger.debug("Error in link status callback: %s", exc)

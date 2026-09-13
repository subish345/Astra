"""Video ingestion service and frame queue management for ASTRA-EA.

Provides threaded ingestion, bounded queue buffering, frame-drop detection,
and real-time capture FPS calculation.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
import numpy as np

from core.camera.interface import CameraSource, FrameData
from core.common.logging import get_logger
from core.health.types import HealthState

logger = get_logger("CAMERA")


@dataclass
class FramePacket:
    """High-level normalized frame packet passed to the perception scheduler."""
    frame_id: int
    image: np.ndarray
    timestamp_mono: float
    timestamp_wall: datetime
    source_id: str
    width: int
    height: int
    capture_fps: float

    @classmethod
    def from_frame_data(cls, fd: FrameData, capture_fps: float) -> FramePacket:
        return cls(
            frame_id=fd.frame_id,
            image=fd.image,
            timestamp_mono=fd.timestamp_mono,
            timestamp_wall=fd.timestamp_wall,
            source_id=fd.source_id,
            width=fd.width,
            height=fd.height,
            capture_fps=capture_fps,
        )


class VideoIngestionService:
    """Threaded video ingestion service with bounded queue and frame-drop tracking."""

    def __init__(
        self,
        camera_source: CameraSource,
        buffer_size: int = 8,
        drop_policy: str = "drop_oldest",  # "drop_oldest" or "drop_newest"
    ):
        self.camera_source = camera_source
        self.buffer_size = max(2, buffer_size)
        self.drop_policy = drop_policy

        self._queue: queue.Queue[FramePacket] = queue.Queue(maxsize=self.buffer_size)
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._total_captured = 0
        self._total_dropped = 0
        self._fps_window_start = time.monotonic()
        self._fps_window_count = 0
        self._current_fps = 0.0
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start the camera source and ingestion worker thread."""
        if self._running:
            return True

        if not self.camera_source.start():
            logger.error("Failed to start underlying camera source.")
            return False

        self._running = True
        self._fps_window_start = time.monotonic()
        self._fps_window_count = 0
        self._total_captured = 0
        self._total_dropped = 0

        self._thread = threading.Thread(target=self._ingestion_loop, name="VideoIngestionWorker", daemon=True)
        self._thread.start()
        logger.info("VideoIngestionService started with buffer size %d", self.buffer_size)
        return True

    def stop(self) -> None:
        """Stop worker thread and underlying camera source."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

        # Drain queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        self.camera_source.stop()
        logger.info("VideoIngestionService stopped.")

    def _ingestion_loop(self) -> None:
        """Continuous background capture loop."""
        while self._running:
            frame_data = self.camera_source.read()
            if frame_data is None:
                if not self.camera_source.is_active:
                    logger.warning("Camera source became inactive. Terminating ingestion loop.")
                    break
                time.sleep(0.005)
                continue

            with self._lock:
                self._total_captured += 1
                self._fps_window_count += 1
                now = time.monotonic()
                elapsed = now - self._fps_window_start
                if elapsed >= 1.0:
                    self._current_fps = round(self._fps_window_count / elapsed, 1)
                    self._fps_window_count = 0
                    self._fps_window_start = now

            packet = FramePacket.from_frame_data(frame_data, self._current_fps)

            # Handle bounded queue full condition
            if self._queue.full():
                with self._lock:
                    self._total_dropped += 1
                if self.drop_policy == "drop_oldest":
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._queue.put_nowait(packet)
                    except queue.Full:
                        pass
                else:
                    # Drop current newest packet
                    continue
            else:
                self._queue.put_nowait(packet)

    def get_frame(self, timeout: float = 0.5) -> Optional[FramePacket]:
        """Fetch the next available frame packet."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def current_fps(self) -> float:
        with self._lock:
            return self._current_fps

    @property
    def total_captured(self) -> int:
        with self._lock:
            return self._total_captured

    @property
    def total_dropped(self) -> int:
        with self._lock:
            return self._total_dropped + self.camera_source.get_dropped_frames()

    @property
    def is_running(self) -> bool:
        return self._running and (self._thread.is_alive() if self._thread else False)

    def get_health_state(self) -> Tuple[HealthState, str]:
        """Evaluate ingestion health status."""
        if not self._running:
            return HealthState.NORMAL, "Ingestion stopped"

        if not self.camera_source.is_active:
            return HealthState.FAILED, "Camera source disconnected or inactive"

        dropped = self.total_dropped
        captured = self._total_captured
        if captured > 30 and (dropped / captured) > 0.3:
            return HealthState.DEGRADED, f"High frame drop rate ({dropped}/{captured} dropped)"

        return HealthState.NORMAL, f"Capture healthy ({self._current_fps:.1f} FPS, {dropped} dropped)"

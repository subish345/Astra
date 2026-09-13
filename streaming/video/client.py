# ==============================================================================
# ASTRA-EA Video Stream Client
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Background IP video stream client receiving multipart MJPEG streams with auto-reconnect."""

from __future__ import annotations

import logging
import threading
import time
import urllib.request
from typing import Callable, Dict, Optional, Tuple
import cv2
import numpy as np

from streaming.protocol.base import IStreamClient

logger = logging.getLogger("video_client")


class VideoStreamClient(IStreamClient):
    """Client worker reading MJPEG video over HTTP with auto-reconnection and drop detection."""

    def __init__(
        self,
        stream_url: str = "http://127.0.0.1:8554/video",
        on_frame_callback: Optional[Callable[[np.ndarray, Dict[str, float]], None]] = None,
        on_status_callback: Optional[Callable[[bool, str], None]] = None,
        reconnect_interval_seconds: float = 2.0,
    ) -> None:
        self.stream_url = stream_url
        self.on_frame = on_frame_callback
        self.on_status = on_status_callback
        self.reconnect_interval = reconnect_interval_seconds

        self._running = False
        self._connected = False
        self._thread: Optional[threading.Thread] = None

        # Metrics
        self.frames_received: int = 0
        self.reconnect_count: int = 0
        self.stream_fps: float = 0.0
        self.last_frame_time: float = 0.0
        self._fps_counter: int = 0
        self._last_fps_calc: float = time.perf_counter()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Start background connection thread."""
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(
            target=self._client_loop,
            daemon=True,
            name="astra_video_client",
        )
        self._thread.start()
        return True

    def disconnect(self) -> None:
        """Stop client and terminate connection."""
        self._running = False
        self._connected = False
        if self.on_status:
            try:
                self.on_status(False, "DISCONNECTED")
            except Exception:
                pass

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Video stream client stopped.")

    def _client_loop(self) -> None:
        """Continuous connection and stream parsing loop with reconnection."""
        while self._running:
            try:
                logger.info("Connecting to video stream at %s...", self.stream_url)
                req = urllib.request.Request(
                    self.stream_url,
                    headers={"User-Agent": "ASTRA-EA-GroundMonitor/1.0"},
                )
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    self._connected = True
                    if self.on_status:
                        try:
                            self.on_status(True, "CONNECTED")
                        except Exception:
                            pass
                    logger.info("Connected to video stream at %s", self.stream_url)

                    stream_bytes = b""
                    while self._running:
                        chunk = response.read(4096)
                        if not chunk:
                            break
                        stream_bytes += chunk

                        # Look for JPEG frame delimiters
                        a = stream_bytes.find(b"\xff\xd8")  # JPEG start
                        b = stream_bytes.find(b"\xff\xd9")  # JPEG end
                        if a != -1 and b != -1:
                            if a < b:
                                jpg_data = stream_bytes[a : b + 2]
                                stream_bytes = stream_bytes[b + 2 :]

                                frame = cv2.imdecode(np.frombuffer(jpg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                                if frame is not None:
                                    self._handle_frame(frame)
                            else:
                                # Start is after end; discard corrupt bytes before start
                                stream_bytes = stream_bytes[a:]

            except Exception as exc:
                self._connected = False
                if self.on_status:
                    try:
                        self.on_status(False, f"LINK_LOST ({type(exc).__name__})")
                    except Exception:
                        pass
                logger.debug("Video stream disconnected: %s. Reconnecting in %.1fs...", exc, self.reconnect_interval)
                self.reconnect_count += 1

            if self._running:
                time.sleep(self.reconnect_interval)

    def _handle_frame(self, frame: np.ndarray) -> None:
        """Process successfully decoded frame and compute client FPS."""
        now = time.perf_counter()
        self.frames_received += 1
        self.last_frame_time = now

        self._fps_counter += 1
        elapsed = now - self._last_fps_calc
        if elapsed >= 1.0:
            self.stream_fps = round(self._fps_counter / elapsed, 1)
            self._fps_counter = 0
            self._last_fps_calc = now

        if self.on_frame:
            metrics = {
                "fps": self.stream_fps,
                "frames_received": float(self.frames_received),
                "reconnect_count": float(self.reconnect_count),
                "timestamp": now,
            }
            try:
                self.on_frame(frame, metrics)
            except Exception as exc:
                logger.error("Error in frame callback: %s", exc)

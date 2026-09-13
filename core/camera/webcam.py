"""OpenCV-based physical camera source for ASTRA-EA.

Supports local webcams, USB video class (UVC) devices, and MIPI cameras.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional, Tuple
import cv2
import numpy as np

from core.camera.interface import CameraSource, FrameData
from core.common.logging import get_logger

logger = get_logger("CAMERA")


class WebcamSource(CameraSource):
    """Real-time camera feed capture utilizing OpenCV VideoCapture."""

    def __init__(
        self,
        device_id: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        auto_reconnect: bool = True,
    ):
        self.device_id = device_id
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        self.auto_reconnect = auto_reconnect

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_count = 0
        self._is_active = False
        self._status = "CLOSED"
        self._actual_width = width
        self._actual_height = height
        self._actual_fps = float(fps)

    def start(self) -> bool:
        """Open camera capture device and configure parameters."""
        logger.info("Opening camera device %d...", self.device_id)
        try:
            self._cap = cv2.VideoCapture(self.device_id)
            if not self._cap or not self._cap.isOpened():
                logger.error("Failed to open camera device %d", self.device_id)
                self._status = "ERROR"
                self._is_active = False
                return False

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
            self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            self._actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or self.target_width)
            self._actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.target_height)
            self._actual_fps = float(self._cap.get(cv2.CAP_PROP_FPS) or self.target_fps)

            self._is_active = True
            self._status = "OPEN"
            logger.info(
                "Camera %d online: %dx%d @ %.1f FPS",
                self.device_id,
                self._actual_width,
                self._actual_height,
                self._actual_fps,
            )
            return True
        except Exception as exc:
            logger.error("Exception opening camera device %d: %s", self.device_id, exc)
            self._status = "ERROR"
            self._is_active = False
            return False

    def stop(self) -> None:
        """Release camera device resources."""
        if self._cap:
            try:
                self._cap.release()
            except Exception as exc:
                logger.warning("Error releasing camera: %s", exc)
            self._cap = None
        self._is_active = False
        self._status = "CLOSED"
        logger.info("Camera device %d released.", self.device_id)

    def read(self) -> Optional[FrameData]:
        """Fetch the next available frame with monotonic and wall-clock timestamps."""
        if not self._is_active or not self._cap:
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            logger.warning("Camera %d dropped frame or disconnected.", self.device_id)
            self._status = "DEGRADED"
            return None

        self._frame_count += 1
        now_mono = time.monotonic()
        now_wall = datetime.now(timezone.utc)

        return FrameData(
            frame_id=self._frame_count,
            image=frame,
            timestamp_mono=now_mono,
            timestamp_wall=now_wall,
            source_id=f"webcam:{self.device_id}",
        )

    def get_status(self) -> str:
        return self._status

    def get_fps(self) -> float:
        return self._actual_fps

    def get_resolution(self) -> Tuple[int, int]:
        return (self._actual_width, self._actual_height)

    @property
    def is_active(self) -> bool:
        return self._is_active

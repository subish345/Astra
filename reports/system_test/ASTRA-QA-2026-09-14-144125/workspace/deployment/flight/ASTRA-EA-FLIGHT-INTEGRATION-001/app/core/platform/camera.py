"""Flight-Like Camera Abstraction and Driver Interface for ASTRA-EA (Phase 18).

In accordance with Section 14 & 15:
Abstracts sensor hardware away from perception. Enforces deterministic camera failure
handling: CAMERA_FAILED -> PERCEPTION_DEGRADED -> PROCEDURE_VERIFICATION_PAUSED.
Prohibits the use of stale frames for verification decisions.
"""

from __future__ import annotations

import abc
import enum
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np

from core.platform.clock import FrameTimestamp, MissionClock


class CameraState(str, enum.Enum):
    UNINITIALIZED = "UNINITIALIZED"
    READY = "READY"
    STREAMING = "STREAMING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


@dataclass
class CameraHealth:
    state: CameraState
    fps: float
    frame_count: int
    consecutive_drop_count: int
    last_frame_timestamp: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "fps": self.fps,
            "frame_count": self.frame_count,
            "consecutive_drop_count": self.consecutive_drop_count,
            "last_frame_timestamp": self.last_frame_timestamp,
            "error_message": self.error_message,
        }


class CameraDriver(abc.ABC):
    """Abstract Flight Camera Driver Interface (D18.05)."""

    def __init__(self, clock: Optional[MissionClock] = None) -> None:
        self.clock = clock or MissionClock()
        self.state = CameraState.UNINITIALIZED
        self.frame_count: int = 0
        self.consecutive_drops: int = 0
        self._fps: float = 0.0
        self._last_frame_time: float = 0.0
        self._last_stamped_frame: Optional[np.ndarray] = None
        self._last_frame_timestamp: Optional[FrameTimestamp] = None
        self.error_message: Optional[str] = None

    @abc.abstractmethod
    def initialize(self) -> bool:
        """Initialize camera hardware/connection."""
        pass

    @abc.abstractmethod
    def start(self) -> bool:
        """Begin camera frame streaming."""
        pass

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop camera frame acquisition."""
        pass

    @abc.abstractmethod
    def _acquire_raw_frame(self) -> Optional[np.ndarray]:
        """Hardware-specific raw frame read."""
        pass

    def read_frame(self) -> Optional[Tuple[np.ndarray, FrameTimestamp]]:
        """Acquire a new frame and stamp it.

        CRITICAL RULE (Section 15):
        If frame acquisition fails, state transitions to CAMERA_FAILED.
        Stale frames are NEVER returned or reused for assurance decisions.
        """
        if self.state not in (CameraState.STREAMING, CameraState.READY):
            return None

        raw = self._acquire_raw_frame()
        now = time.monotonic()

        if raw is None:
            self.consecutive_drops += 1
            if self.consecutive_drops >= 5:
                self.state = CameraState.FAILED
                self.error_message = f"Camera read timeout: {self.consecutive_drops} consecutive dropped frames"
            return None

        self.consecutive_drops = 0
        self.frame_count += 1

        if self._last_frame_time > 0:
            dt = now - self._last_frame_time
            if dt > 0:
                self._fps = round(0.9 * self._fps + 0.1 * (1.0 / dt), 1)
        self._last_frame_time = now

        ts = self.clock.stamp_frame(self.frame_count)
        self._last_frame_timestamp = ts
        self._last_stamped_frame = raw
        return raw, ts

    def health(self) -> CameraHealth:
        """Return standardized health status."""
        return CameraHealth(
            state=self.state,
            fps=self._fps,
            frame_count=self.frame_count,
            consecutive_drop_count=self.consecutive_drops,
            last_frame_timestamp=self._last_frame_timestamp.utc_iso if self._last_frame_timestamp else None,
            error_message=self.error_message,
        )

    def timestamp(self) -> Optional[FrameTimestamp]:
        """Get timestamp of most recently acquired valid frame."""
        return self._last_frame_timestamp


class SimulatedCameraDriver(CameraDriver):
    """Simulated camera driver for testing and HIL scenarios."""

    def __init__(
        self,
        clock: Optional[MissionClock] = None,
        width: int = 1280,
        height: int = 720,
        fps_target: float = 30.0,
    ) -> None:
        super().__init__(clock)
        self.width = width
        self.height = height
        self.fps_target = fps_target
        self._inject_failure: bool = False

    def initialize(self) -> bool:
        self.state = CameraState.READY
        return True

    def start(self) -> bool:
        if self.state != CameraState.READY:
            return False
        self.state = CameraState.STREAMING
        return True

    def stop(self) -> None:
        self.state = CameraState.STOPPED

    def inject_failure(self, fail: bool = True) -> None:
        """Inject camera hardware disconnection for HIL validation."""
        self._inject_failure = fail
        if fail:
            self.consecutive_drops = 5
            self.state = CameraState.FAILED
            self.error_message = "Simulated hardware sensor failure injected"

    def _acquire_raw_frame(self) -> Optional[np.ndarray]:
        if self._inject_failure:
            return None
        # Generate synthetic RGB frame
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Subtle gradient background
        frame[:, :, 0] = np.linspace(20, 60, self.width, dtype=np.uint8)
        frame[:, :, 1] = np.linspace(30, 80, self.width, dtype=np.uint8)
        frame[:, :, 2] = np.linspace(40, 100, self.width, dtype=np.uint8)
        return frame


class RealV4L2CameraDriver(CameraDriver):
    """Production V4L2 camera driver (e.g. Sony IMX477 or USB COTS)."""

    def __init__(
        self,
        device_id: int = 0,
        clock: Optional[MissionClock] = None,
        width: int = 1920,
        height: int = 1080,
    ) -> None:
        super().__init__(clock)
        self.device_id = device_id
        self.width = width
        self.height = height
        self._cap = None

    def initialize(self) -> bool:
        try:
            import cv2
            self._cap = cv2.VideoCapture(self.device_id)
            if not self._cap.isOpened():
                self.state = CameraState.FAILED
                self.error_message = f"Cannot open V4L2 device {self.device_id}"
                return False
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.state = CameraState.READY
            return True
        except Exception as e:
            self.state = CameraState.FAILED
            self.error_message = str(e)
            return False

    def start(self) -> bool:
        if self.state != CameraState.READY:
            return False
        self.state = CameraState.STREAMING
        return True

    def stop(self) -> None:
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
        self.state = CameraState.STOPPED

    def _acquire_raw_frame(self) -> Optional[np.ndarray]:
        if not self._cap or not self._cap.isOpened():
            return None
        try:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                return None
            return frame
        except Exception as e:
            self.error_message = str(e)
            return None

"""File-based video source for ASTRA-EA simulation and test replay.

Reads recorded video files (.mp4, .avi, .mkv) with optional real-time playback pacing
and loop capabilities.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple
import cv2

from core.camera.interface import CameraSource, FrameData
from core.common.logging import get_logger

logger = get_logger("CAMERA")


class VideoFileSource(CameraSource):
    """Feeds video frames sequentially from a local video file."""

    def __init__(
        self,
        file_path: str | Path,
        loop: bool = False,
        realtime_pacing: bool = False,
    ):
        self.file_path = Path(file_path)
        self.loop = loop
        self.realtime_pacing = realtime_pacing

        self._cap: Optional[cv2.VideoCapture] = None
        self._frame_count = 0
        self._is_active = False
        self._status = "CLOSED"
        self._fps = 30.0
        self._width = 1280
        self._height = 720
        self._last_frame_mono: Optional[float] = None

    def start(self) -> bool:
        """Open video file for playback."""
        if not self.file_path.exists():
            logger.error("Video file does not exist: %s", self.file_path)
            self._status = "ERROR"
            return False

        self._cap = cv2.VideoCapture(str(self.file_path))
        if not self._cap or not self._cap.isOpened():
            logger.error("Failed to open video file: %s", self.file_path)
            self._status = "ERROR"
            return False

        self._fps = float(self._cap.get(cv2.CAP_PROP_FPS) or 30.0)
        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
        self._is_active = True
        self._status = "OPEN"
        self._frame_count = 0
        self._last_frame_mono = time.monotonic()
        logger.info("Video file %s opened: %dx%d @ %.1f FPS", self.file_path.name, self._width, self._height, self._fps)
        return True

    def stop(self) -> None:
        """Close video file."""
        if self._cap:
            self._cap.release()
            self._cap = None
        self._is_active = False
        self._status = "CLOSED"

    def read(self) -> Optional[FrameData]:
        """Read next frame from video file."""
        if not self._is_active or not self._cap:
            return None

        # Optional pacing to simulate live stream
        if self.realtime_pacing and self._last_frame_mono and self._fps > 0:
            target_delta = 1.0 / self._fps
            elapsed = time.monotonic() - self._last_frame_mono
            if elapsed < target_delta:
                time.sleep(target_delta - elapsed)

        ret, frame = self._cap.read()
        if not ret or frame is None:
            if self.loop:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    self._status = "COMPLETED"
                    self._is_active = False
                    return None
            else:
                self._status = "COMPLETED"
                self._is_active = False
                return None

        self._frame_count += 1
        now_mono = time.monotonic()
        now_wall = datetime.now(timezone.utc)
        self._last_frame_mono = now_mono

        return FrameData(
            frame_id=self._frame_count,
            image=frame,
            timestamp_mono=now_mono,
            timestamp_wall=now_wall,
            source_id=f"file:{self.file_path.name}",
        )

    def get_status(self) -> str:
        return self._status

    def get_fps(self) -> float:
        return self._fps

    def get_resolution(self) -> Tuple[int, int]:
        return (self._width, self._height)

    def get_source_id(self) -> str:
        return f"file:{self.file_path.name}"

    def get_dropped_frames(self) -> int:
        return 0

    @property
    def is_active(self) -> bool:
        return self._is_active

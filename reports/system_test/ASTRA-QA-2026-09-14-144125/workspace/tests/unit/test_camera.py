"""Unit tests for camera and video ingestion abstractions."""

import time
from datetime import datetime, timezone
import numpy as np
import pytest

from core.camera.file_source import VideoFileSource
from core.camera.interface import CameraSource, FrameData
from core.camera.webcam import WebcamSource


def test_frame_data_properties():
    """Verify FrameData container dimensions and properties."""
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    frame = FrameData(
        frame_id=1,
        image=img,
        timestamp_mono=time.monotonic(),
        timestamp_wall=datetime.now(timezone.utc),
        source_id="test_cam",
    )
    assert frame.height == 720
    assert frame.width == 1280
    assert frame.channels == 3
    assert frame.frame_id == 1


def test_video_file_source_non_existent():
    """Verify VideoFileSource fails gracefully on non-existent file."""
    src = VideoFileSource("non_existent_video.mp4")
    success = src.start()
    assert success is False
    assert src.get_status() == "ERROR"
    assert src.read() is None
    assert src.is_active is False


class MockCameraSource(CameraSource):
    """Synthetic test camera producing deterministic frames."""

    def __init__(self, total_frames: int = 5):
        self.total_frames = total_frames
        self.current = 0
        self._active = False

    def start(self) -> bool:
        self._active = True
        return True

    def stop(self) -> None:
        self._active = False

    def read(self):
        if not self._active or self.current >= self.total_frames:
            return None
        self.current += 1
        return FrameData(
            frame_id=self.current,
            image=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp_mono=time.monotonic(),
            timestamp_wall=datetime.now(timezone.utc),
            source_id="mock",
        )

    def get_status(self) -> str:
        return "OPEN" if self._active else "CLOSED"

    def get_fps(self) -> float:
        return 30.0

    def get_resolution(self):
        return (640, 480)

    def get_source_id(self) -> str:
        return "mock_camera"

    def get_dropped_frames(self) -> int:
        return 0

    @property
    def is_active(self) -> bool:
        return self._active


def test_camera_source_contract():
    """Verify standard usage pattern against CameraSource abstraction."""
    cam: CameraSource = MockCameraSource(total_frames=3)
    assert cam.start() is True
    assert cam.is_active is True

    frames = []
    while True:
        f = cam.read()
        if f is None:
            break
        frames.append(f)

    assert len(frames) == 3
    assert [f.frame_id for f in frames] == [1, 2, 3]

    cam.stop()
    assert cam.is_active is False

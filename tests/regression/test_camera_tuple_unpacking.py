"""Regression Test for FINDING-001 / CAPA-001: Camera driver tuple return unpacking."""

import numpy as np
import pytest

from core.operations.precheck import PreMissionRunner


class MockTupleCameraDriver:
    """Simulates CameraDriver returning Optional[Tuple[np.ndarray, int]]."""

    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed

    def initialize(self) -> bool:
        return True

    def start(self) -> bool:
        return True

    def stop(self) -> None:
        pass

    def read_frame(self):
        if self.should_succeed:
            dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            timestamp_ns = 1726245000000000000
            return (dummy_frame, timestamp_ns)
        return None


def test_camera_tuple_unpacking_success(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Verify precheck safely unpacks (frame, timestamp) tuple without AttributeError."""
    monkeypatch.setattr(
        "core.platform.camera.SimulatedCameraDriver",
        lambda *args, **kwargs: MockTupleCameraDriver(should_succeed=True),
    )

    runner = PreMissionRunner(project_root=tmp_path)
    res = runner._check_camera()
    assert res.status == "PASS"
    assert "1280x720" in res.details


def test_camera_tuple_unpacking_timeout_handled(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Verify precheck handles None return cleanly when sensor times out."""
    monkeypatch.setattr(
        "core.platform.camera.SimulatedCameraDriver",
        lambda *args, **kwargs: MockTupleCameraDriver(should_succeed=False),
    )

    runner = PreMissionRunner(project_root=tmp_path)
    res = runner._check_camera()
    assert res.status == "FAIL"
    assert "Camera driver returned empty frame" in res.details

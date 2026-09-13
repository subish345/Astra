"""Contract tests for SimulatedCameraSource (D8.04, D8.08)."""

from __future__ import annotations

import numpy as np
import pytest

from core.camera.interface import CameraSource, FrameData
from core.simulation.camera_sim import SimulatedCameraSource
from core.simulation.scenario import FaultTrigger, FaultType, SimulationScenario


def test_simulated_camera_lifecycle():
    """Verify camera implements CameraSource contract and lifecycle."""
    scen = SimulationScenario(
        scenario_id="TEST_CAM_001",
        duration_sec=1.0,
        target_fps=30.0,
        camera_profile="VIEW_LEFT",
    )
    cam = SimulatedCameraSource(scenario=scen, width=320, height=240)
    assert isinstance(cam, CameraSource)
    assert not cam.is_active
    assert cam.get_status() == "CLOSED"
    assert cam.get_resolution() == (320, 240)
    assert cam.get_fps() == 30.0

    assert cam.start()
    assert cam.is_active
    assert cam.get_status() == "OPEN"

    frame = cam.read()
    assert frame is not None
    assert isinstance(frame, FrameData)
    assert frame.image.shape == (240, 320, 3)
    assert frame.frame_id == 1
    assert "VIEW_LEFT" in frame.source_id

    cam.stop()
    assert not cam.is_active
    assert cam.get_status() == "CLOSED"


def test_simulated_camera_black_frame_injection():
    """Verify black frame injection returns an all-zero frame."""
    scen = SimulationScenario(
        scenario_id="TEST_BLACK_001",
        duration_sec=2.0,
        target_fps=30.0,
        faults=[
            FaultTrigger(
                fault_type=FaultType.BLACK_FRAME,
                start_time=0.0,
                duration_sec=1.0,
                intensity=1.0,
            )
        ],
    )
    cam = SimulatedCameraSource(scenario=scen, width=160, height=120)
    assert cam.start()

    frame = cam.read()
    assert frame is not None
    assert np.all(frame.image == 0)

    cam.stop()


def test_simulated_camera_frame_drop():
    """Verify frame drop fault returns None and increments dropped frame counter."""
    scen = SimulationScenario(
        scenario_id="TEST_DROP_001",
        duration_sec=2.0,
        target_fps=30.0,
        faults=[
            FaultTrigger(
                fault_type=FaultType.FRAME_DROP,
                start_time=0.0,
                duration_sec=1.0,
                intensity=1.0,
                frequency=1.0,  # 100% drop rate
            )
        ],
    )
    cam = SimulatedCameraSource(scenario=scen, width=160, height=120)
    assert cam.start()

    # Read should return None due to frame drop
    frame = cam.read()
    assert frame is None
    assert cam.get_dropped_frames() == 1

    cam.stop()


def test_simulated_camera_viewpoint_switch():
    """Verify viewpoint switch dynamically alters camera profile."""
    scen = SimulationScenario(
        scenario_id="TEST_SWITCH_001",
        duration_sec=2.0,
        target_fps=30.0,
        camera_profile="VIEW_LEFT",
        faults=[
            FaultTrigger(
                fault_type=FaultType.VIEWPOINT_SWITCH,
                start_time=0.0,
                duration_sec=2.0,
                intensity=1.0,
                target="VIEW_RIGHT",
            )
        ],
    )
    cam = SimulatedCameraSource(scenario=scen, width=160, height=120)
    assert cam.start()

    frame = cam.read()
    assert frame is not None
    assert cam.current_camera_profile == "VIEW_RIGHT"
    assert "VIEW_RIGHT" in frame.source_id

    cam.stop()

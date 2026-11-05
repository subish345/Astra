import numpy as np

from core.perception.types import BoundingBox, Keypoint, PerceptionState, PoseObservation, Track, TrackState
from core.perception.visualizer import OverlayConfig, PerceptionVisualizer


def test_normal_overlay_hides_lost_tracks():
    state = PerceptionState(1, 1, "test", tracks=[Track(1, "person", BoundingBox(10, 10, 80, 80), 0.9,
        state=TrackState.TEMPORARILY_LOST, lost_frames=1)])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    config = OverlayConfig(show_hud=False, show_laser_guides=False)
    baseline = PerceptionVisualizer(config).render(frame, PerceptionState(1, 1, "test"))
    assert np.array_equal(PerceptionVisualizer(config).render(frame, state), baseline)
    config.show_lost_tracks = True
    assert not np.array_equal(PerceptionVisualizer(config).render(frame, state), baseline)


def test_invisible_or_offscreen_joints_are_not_drawn():
    state = PerceptionState(1, 1, "test", poses=[PoseObservation(1, [
        Keypoint(20, 20, 0.1, name="left_wrist"),
        Keypoint(-10, 30, 0.9, name="left_elbow"),
    ], 0.9)])
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    config = OverlayConfig(show_hud=False, show_laser_guides=False)
    baseline = PerceptionVisualizer(config).render(frame, PerceptionState(1, 1, "test"))
    assert np.array_equal(PerceptionVisualizer(config).render(frame, state), baseline)


def test_detector_duplicate_filter():
    from core.perception.detection.general_adapter import filter_detections
    from core.perception.types import Detection
    detections = [Detection("cell phone", 0.9, BoundingBox(10, 10, 50, 50)),
                  Detection("cell phone", 0.8, BoundingBox(11, 11, 51, 51)),
                  Detection("cup", 0.9, BoundingBox(10, 10, 50, 50)),
                  Detection("person", 0.9, BoundingBox(-10, -10, -1, -1))]
    result = filter_detections(detections, 100, 100)
    assert [item.class_name for item in result] == ["cell phone", "cup"]

"""Unit tests for perception data structures and geometry calculations."""

import pytest

from core.perception.types import (
    BoundingBox,
    Detection,
    HandObservation,
    HandType,
    Keypoint,
    LatencyBreakdown,
    PerceptionState,
    PoseObservation,
    Track,
    TrackState,
)


def test_bounding_box_geometry():
    """Verify BoundingBox dimensions, center point, and area."""
    bbox = BoundingBox(x1=100.0, y1=200.0, x2=300.0, y2=400.0)
    assert bbox.width == 200.0
    assert bbox.height == 200.0
    assert bbox.area == 40000.0
    assert bbox.center == (200.0, 300.0)


def test_bounding_box_iou():
    """Verify Intersection-over-Union (IoU) calculation."""
    b1 = BoundingBox(x1=0.0, y1=0.0, x2=10.0, y2=10.0)
    b2 = BoundingBox(x1=5.0, y1=0.0, x2=15.0, y2=10.0)

    # Intersection: 5x10 = 50. Union: 100 + 100 - 50 = 150. IoU = 50/150 = 0.3333...
    assert b1.iou(b2) == pytest.approx(1.0 / 3.0)

    # Disjoint boxes
    b3 = BoundingBox(x1=50.0, y1=50.0, x2=60.0, y2=60.0)
    assert b1.iou(b3) == 0.0


def test_pose_observation_keypoints():
    """Verify Keypoint lookup on PoseObservation."""
    kps = [
        Keypoint(x=10.0, y=20.0, confidence=0.9, name="nose"),
        Keypoint(x=30.0, y=40.0, confidence=0.85, name="left_wrist"),
    ]
    pose = PoseObservation(person_id=1, keypoints=kps, confidence=0.9)
    assert pose.get_keypoint("nose") is not None
    assert pose.get_keypoint("nose").x == 10.0
    assert pose.get_keypoint("non_existent") is None


def test_track_lifecycle_states():
    """Verify Track state transitions."""
    track = Track(
        track_id=1,
        class_name="RED_BOX",
        bbox=BoundingBox(0, 0, 10, 10),
        confidence=0.9,
        state=TrackState.VISIBLE,
    )
    assert track.state == TrackState.VISIBLE
    track.state = TrackState.TEMPORARILY_LOST
    assert track.state == TrackState.TEMPORARILY_LOST
    track.state = TrackState.REACQUIRED
    assert track.state == TrackState.REACQUIRED

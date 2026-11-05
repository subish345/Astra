"""Unit tests for MultiObjectTracker and occlusion handling."""

import pytest

from core.perception.tracking.tracker import MultiObjectTracker
from core.perception.types import BoundingBox, Detection, TrackState


def test_tracker_id_continuity():
    """Verify that a moving object retains the same track ID across frames."""
    tracker = MultiObjectTracker(iou_threshold=0.2, max_lost_frames=5)

    # Frame 1: Object at (100, 100) -> (150, 150)
    det1 = [Detection("RED_BOX", 0.9, BoundingBox(100, 100, 150, 150))]
    tracks1 = tracker.update(det1, frame_id=1)
    assert len(tracks1) == 1
    tid = tracks1[0].track_id

    # Frame 2: Object shifted slightly to (105, 105) -> (155, 155)
    det2 = [Detection("RED_BOX", 0.9, BoundingBox(105, 105, 155, 155))]
    tracks2 = tracker.update(det2, frame_id=2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == tid
    assert tracks2[0].state == TrackState.VISIBLE
    assert tracks2[0].velocity == (5.0, 5.0)


def test_tracker_temporary_occlusion_and_reacquisition():
    """Verify occlusion grace period and reacquisition."""
    tracker = MultiObjectTracker(iou_threshold=0.2, max_lost_frames=3)

    # Frame 1: Object visible
    det1 = [Detection("RED_BOX", 0.9, BoundingBox(100, 100, 150, 150))]
    tracks1 = tracker.update(det1, frame_id=1)
    tid = tracks1[0].track_id

    # Frame 2: Object disappears (occluded by astronaut hand)
    tracks2 = tracker.update([], frame_id=2)
    assert len(tracks2) == 1
    assert tracks2[0].track_id == tid
    assert tracks2[0].state == TrackState.TEMPORARILY_LOST
    assert tracks2[0].lost_frames == 1

    # Frame 3: Object reappears
    det3 = [Detection("RED_BOX", 0.9, BoundingBox(102, 102, 152, 152))]
    tracks3 = tracker.update(det3, frame_id=3)
    assert len(tracks3) == 1
    assert tracks3[0].track_id == tid
    assert tracks3[0].state == TrackState.REACQUIRED


def test_tracker_drops_after_max_lost():
    """Verify that track is pruned if missing beyond max_lost_frames."""
    tracker = MultiObjectTracker(iou_threshold=0.2, max_lost_frames=2)

    # Frame 1: Object visible
    tracker.update([Detection("RED_BOX", 0.9, BoundingBox(100, 100, 150, 150))], frame_id=1)

    # Frames 2 and 3: Object missing (within grace period)
    tracker.update([], frame_id=2)
    tracker.update([], frame_id=3)

    # Frame 4: Exceeds max_lost_frames=2 -> pruned
    tracks4 = tracker.update([], frame_id=4)
    assert len(tracks4) == 0

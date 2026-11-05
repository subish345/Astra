"""Automated tests for Adaptive Inference Scheduler and Latest-Frame Queue (D10.17, D10.18)."""

import numpy as np
import pytest
from core.camera.interface import FrameData
from core.optimization.scheduler import (
    AdaptiveInferenceScheduler,
    SchedulerCadence,
    LatestFrameQueue,
)
from core.perception.types import BoundingBox, Detection, PoseObservation, HandObservation


def _make_dummy_frame(frame_id: int) -> FrameData:
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    return FrameData(
        frame_id=frame_id,
        image=img,
        timestamp_mono=float(frame_id) * 0.033,
        timestamp_wall=float(frame_id) * 0.033,
        source_id="test_cam",
    )


def test_scheduler_cadence_intervals():
    cadence = SchedulerCadence(
        tracking_interval=1,
        detection_interval=2,
        pose_interval=3,
        hand_interval=3,
        max_cache_age_frames=3,
    )
    sched = AdaptiveInferenceScheduler(cadence=cadence)

    # Frame 0
    assert sched.should_run_tracking() is True
    assert sched.should_run_detection() is True
    assert sched.should_run_pose() is True
    assert sched.should_run_hands() is True

    sched.step()
    # Frame 1
    assert sched.should_run_tracking() is True
    assert sched.should_run_detection() is False
    assert sched.should_run_pose() is False
    assert sched.should_run_hands() is False

    sched.step()
    # Frame 2
    assert sched.should_run_tracking() is True
    assert sched.should_run_detection() is True
    assert sched.should_run_pose() is False
    assert sched.should_run_hands() is False

    sched.step()
    # Frame 3
    assert sched.should_run_tracking() is True
    assert sched.should_run_detection() is False
    assert sched.should_run_pose() is True
    assert sched.should_run_hands() is True


def test_scheduler_observation_caching_and_expiration():
    cadence = SchedulerCadence(
        detection_interval=2,
        max_cache_age_frames=2,
    )
    sched = AdaptiveInferenceScheduler(cadence=cadence)

    dummy_det = [Detection(class_name="RED_BOX", confidence=0.95, bbox=BoundingBox(10, 10, 50, 50))]
    sched.update_detections(dummy_det)

    # Frame 0: fresh
    assert len(sched.get_detections()) == 1
    assert sched.get_detections()[0].class_name == "RED_BOX"

    # Frame 1: cached (age 1)
    sched.step()
    assert len(sched.get_detections()) == 1

    # Frame 2: cached (age 2, still <= max_cache_age_frames=2)
    sched.step()
    assert len(sched.get_detections()) == 1

    # Frame 3: expired (age 3 > 2)
    sched.step()
    assert len(sched.get_detections()) == 0


def test_scheduler_pose_and_hands_caching():
    from core.perception.types import Keypoint, HandType

    cadence = SchedulerCadence(max_cache_age_frames=1)
    sched = AdaptiveInferenceScheduler(cadence=cadence)

    kp = Keypoint(x=100.0, y=100.0, confidence=0.9, name="nose")
    pose = PoseObservation(person_id=1, keypoints=[kp], confidence=0.9)
    hands = [HandObservation(hand_type=HandType.RIGHT, keypoints=[kp], confidence=0.85, wrist=(100.0, 100.0))]

    sched.update_pose(pose)
    sched.update_hands(hands)

    assert sched.get_pose() is not None
    assert len(sched.get_hands()) == 1

    sched.step()
    assert sched.get_pose() is not None
    assert len(sched.get_hands()) == 1

    sched.step()  # age 2 > 1
    assert sched.get_pose() is None
    assert len(sched.get_hands()) == 0


def test_latest_frame_queue_bounded_and_drop_oldest():
    q = LatestFrameQueue(maxsize=2)
    assert q.qsize() == 0
    assert q.dropped_count == 0

    # Put 2 frames
    f1 = _make_dummy_frame(1)
    f2 = _make_dummy_frame(2)
    f3 = _make_dummy_frame(3)

    q.put(f1)
    q.put(f2)
    assert q.qsize() == 2
    assert q.dropped_count == 0

    # Put 3rd frame: should drop f1 (oldest) and keep f2, f3
    dropped = q.put(f3)
    assert dropped is True
    assert q.qsize() == 2
    assert q.dropped_count == 1
    assert q.total_pushed == 3

    # Next get should be f2 (not f1!)
    got = q.get(timeout=0.1)
    assert got is not None
    assert got.frame_id == 2

    # Next get should be f3
    got2 = q.get(timeout=0.1)
    assert got2 is not None
    assert got2.frame_id == 3

    assert q.qsize() == 0
    assert q.get(timeout=0.01) is None


def test_latest_frame_queue_clear():
    q = LatestFrameQueue(maxsize=3)
    q.put(_make_dummy_frame(10))
    q.put(_make_dummy_frame(11))
    assert q.qsize() == 2
    cleared = q.clear()
    assert cleared == 2
    assert q.qsize() == 0

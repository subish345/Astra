"""Unit tests for PerceptionScheduler intervals."""

import pytest

from core.perception.scheduler import PerceptionScheduler, SchedulerConfig


def test_scheduler_cadence_intervals():
    """Verify execution triggers according to configured skip intervals."""
    cfg = SchedulerConfig(
        tracking_interval=1,
        detection_interval=2,
        pose_interval=3,
        hand_interval=3,
        quality_interval=4,
    )
    scheduler = PerceptionScheduler(cfg)

    # Frame 1: Tracking only
    assert scheduler.should_run_tracking(1) is True
    assert scheduler.should_run_detection(1) is False
    assert scheduler.should_run_pose(1) is False

    # Frame 2: Tracking and Detection (2 % 2 == 0)
    assert scheduler.should_run_tracking(2) is True
    assert scheduler.should_run_detection(2) is True
    assert scheduler.should_run_pose(2) is False

    # Frame 3: Tracking, Pose, Hands (3 % 3 == 0)
    assert scheduler.should_run_tracking(3) is True
    assert scheduler.should_run_detection(3) is False
    assert scheduler.should_run_pose(3) is True
    assert scheduler.should_run_hands(3) is True

    # Frame 4: Tracking, Detection, Quality (4 % 2 == 0, 4 % 4 == 0)
    assert scheduler.should_run_detection(4) is True
    assert scheduler.should_run_quality(4) is True

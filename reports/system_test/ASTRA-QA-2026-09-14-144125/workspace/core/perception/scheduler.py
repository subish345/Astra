"""Perception scheduler for managing model execution cadences.

Optimizes compute allocation by staggering heavy deep-learning inference tasks
while maintaining high-frequency tracking across every frame.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SchedulerConfig:
    """Frame interval configuration (1 = every frame, 2 = every other frame, etc.)."""
    tracking_interval: int = 1
    detection_interval: int = 1
    pose_interval: int = 1
    hand_interval: int = 1
    quality_interval: int = 2


class PerceptionScheduler:
    """Determines which perception models to trigger for a given frame index."""

    def __init__(self, config: SchedulerConfig = None):
        self.config = config or SchedulerConfig()
        self.detection_runs = 0
        self.pose_runs = 0
        self.hand_runs = 0
        self.tracking_runs = 0
        self.quality_runs = 0

    def should_run_detection(self, frame_id: int) -> bool:
        interval = max(1, self.config.detection_interval)
        run = (frame_id % interval) == 0
        if run:
            self.detection_runs += 1
        return run

    def should_run_pose(self, frame_id: int) -> bool:
        interval = max(1, self.config.pose_interval)
        run = (frame_id % interval) == 0
        if run:
            self.pose_runs += 1
        return run

    def should_run_hands(self, frame_id: int) -> bool:
        interval = max(1, self.config.hand_interval)
        run = (frame_id % interval) == 0
        if run:
            self.hand_runs += 1
        return run

    def should_run_tracking(self, frame_id: int) -> bool:
        interval = max(1, self.config.tracking_interval)
        run = (frame_id % interval) == 0
        if run:
            self.tracking_runs += 1
        return run

    def should_run_quality(self, frame_id: int) -> bool:
        interval = max(1, self.config.quality_interval)
        run = (frame_id % interval) == 0
        if run:
            self.quality_runs += 1
        return run

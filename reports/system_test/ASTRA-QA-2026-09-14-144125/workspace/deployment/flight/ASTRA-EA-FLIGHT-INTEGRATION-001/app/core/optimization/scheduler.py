"""Adaptive Perception Scheduler and Bounded Latest-Frame Queue for ASTRA-EA.

Implements configurable decoupled inference cadences:
- High-rate tracking (every frame, 1:1)
- Medium-rate object detection (e.g., 1:1 or 1:2)
- Lower-rate pose and hand estimation (e.g., 1:2 or 1:3)

Maintains stateful observations during skipped perception cycles to preserve
continuous interaction kinematics and temporal activity assurance without evidence dropouts.
Also implements a bounded, drop-oldest latest-frame ingestion queue to prevent lag accumulation.
"""

from __future__ import annotations

import queue
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.perception.types import BoundingBox, Detection, HandObservation, PoseObservation

logger = get_logger("OPTIMIZATION")


@dataclass
class SchedulerCadence:
    """Configurable execution cadence for perception modules."""
    tracking_interval: int = 1       # Run tracking every N frames (1 = every frame)
    detection_interval: int = 1      # Run object detection every N frames
    pose_interval: int = 1           # Run pose estimation every N frames
    hand_interval: int = 1           # Run hand keypoints every N frames
    max_cache_age_frames: int = 5    # Max frames to retain cached perception before invalidating


class AdaptiveInferenceScheduler:
    """Coordinates decoupled perception cadences and provides smooth observation caching."""

    def __init__(self, cadence: Optional[SchedulerCadence] = None) -> None:
        self.cadence = cadence or SchedulerCadence()
        self._frame_count: int = 0

        # Cached observations with age counters
        self._cached_detections: List[Detection] = []
        self._detections_age: int = 0

        self._cached_pose: Optional[PoseObservation] = None
        self._pose_age: int = 0

        self._cached_hands: List[HandObservation] = []
        self._hands_age: int = 0

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def should_run_tracking(self, frame_idx: Optional[int] = None) -> bool:
        idx = frame_idx if frame_idx is not None else self._frame_count
        return (idx % max(1, self.cadence.tracking_interval)) == 0

    def should_run_detection(self, frame_idx: Optional[int] = None) -> bool:
        idx = frame_idx if frame_idx is not None else self._frame_count
        return (idx % max(1, self.cadence.detection_interval)) == 0

    def should_run_pose(self, frame_idx: Optional[int] = None) -> bool:
        idx = frame_idx if frame_idx is not None else self._frame_count
        return (idx % max(1, self.cadence.pose_interval)) == 0

    def should_run_hands(self, frame_idx: Optional[int] = None) -> bool:
        idx = frame_idx if frame_idx is not None else self._frame_count
        return (idx % max(1, self.cadence.hand_interval)) == 0

    def step(self) -> None:
        """Advance the frame counter and increment cache ages."""
        self._frame_count += 1
        self._detections_age += 1
        self._pose_age += 1
        self._hands_age += 1

    def update_detections(self, detections: List[Detection]) -> None:
        """Store freshly computed object detections."""
        self._cached_detections = list(detections)
        self._detections_age = 0

    def get_detections(self) -> List[Detection]:
        """Retrieve latest detections (fresh or valid cached)."""
        if self._detections_age <= self.cadence.max_cache_age_frames:
            return self._cached_detections
        return []

    def update_pose(self, pose: Optional[PoseObservation]) -> None:
        """Store freshly computed pose observation."""
        self._cached_pose = pose
        self._pose_age = 0

    def get_pose(self) -> Optional[PoseObservation]:
        """Retrieve latest pose (fresh or valid cached)."""
        if self._pose_age <= self.cadence.max_cache_age_frames:
            return self._cached_pose
        return None

    def update_hands(self, hands: Optional[List[HandObservation]]) -> None:
        """Store freshly computed hand observations."""
        self._cached_hands = list(hands) if hands else []
        self._hands_age = 0

    def get_hands(self) -> List[HandObservation]:
        """Retrieve latest hands (fresh or valid cached)."""
        if self._hands_age <= self.cadence.max_cache_age_frames:
            return self._cached_hands
        return []

    def get_metrics(self) -> Dict[str, Any]:
        """Return scheduling profile and active cadences."""
        return {
            "total_frames": self._frame_count,
            "cadence": {
                "tracking_interval": self.cadence.tracking_interval,
                "detection_interval": self.cadence.detection_interval,
                "pose_interval": self.cadence.pose_interval,
                "hand_interval": self.cadence.hand_interval,
            },
            "cache_ages": {
                "detections_age": self._detections_age,
                "pose_age": self._pose_age,
                "hands_age": self._hands_age,
            },
        }


class LatestFrameQueue:
    """Thread-safe bounded queue with drop-oldest latest-frame preference.

    Guarantees that real-time processing never falls seconds behind live optical
    sensors by immediately dropping stale buffered frames under compute backpressure.
    """

    def __init__(self, maxsize: int = 2) -> None:
        self.maxsize = max(1, maxsize)
        self._queue: queue.Queue[FrameData] = queue.Queue(maxsize=self.maxsize)
        self._dropped_count: int = 0
        self._total_pushed: int = 0

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    @property
    def total_pushed(self) -> int:
        return self._total_pushed

    def qsize(self) -> int:
        return self._queue.qsize()

    def put(self, frame: FrameData) -> bool:
        """Push frame to queue. If full, drops oldest frame first."""
        self._total_pushed += 1
        dropped_any = False

        if self._queue.full():
            try:
                # Evict oldest frame to maintain latest-frame preference
                self._queue.get_nowait()
                self._dropped_count += 1
                dropped_any = True
            except queue.Empty:
                pass

        try:
            self._queue.put_nowait(frame)
            return dropped_any
        except queue.Full:
            # Race condition safeguard
            self._dropped_count += 1
            return True

    def get(self, timeout: Optional[float] = None) -> Optional[FrameData]:
        """Retrieve next frame from queue."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def clear(self) -> int:
        """Drain all frames from queue and return count of drained frames."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break
        return count

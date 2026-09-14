"""Unified perception pipeline orchestrator for ASTRA-EA.

Orchestrates frame ingestion, quality analysis, scheduled model inferences,
multi-object tracking, latency measurement, and event publishing.
"""

from __future__ import annotations

import time
from typing import List, Optional

from core.camera.ingestion import FramePacket
from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.perception.detection.interface import ObjectDetector
from core.perception.events import (
    HandDetectedEvent,
    ObjectDetectedEvent,
    PerceptionEventBus,
    PerceptionUpdatedEvent,
    PoseUpdatedEvent,
    TrackCreatedEvent,
    TrackLostEvent,
)
from core.perception.hands.interface import HandDetector
from core.perception.pose.interface import PoseEstimator
from core.perception.quality import FrameQualityAnalyzer
from core.perception.scheduler import PerceptionScheduler
from core.perception.tracking.interface import Tracker
from core.perception.types import (
    Detection,
    HandObservation,
    LatencyBreakdown,
    PerceptionState,
    PoseObservation,
    Track,
    TrackState,
)

logger = get_logger("PERCEPTION")


class PerceptionPipeline:
    """End-to-end perception engine coordinating ingestion, AI models, and tracking."""

    def __init__(
        self,
        detector: ObjectDetector,
        pose_estimator: PoseEstimator,
        hand_detector: HandDetector,
        tracker: Tracker,
        scheduler: Optional[PerceptionScheduler] = None,
        quality_analyzer: Optional[FrameQualityAnalyzer] = None,
        event_bus: Optional[PerceptionEventBus] = None,
    ):
        self.detector = detector
        self.pose_estimator = pose_estimator
        self.hand_detector = hand_detector
        self.tracker = tracker
        self.scheduler = scheduler or PerceptionScheduler()
        self.quality_analyzer = quality_analyzer or FrameQualityAnalyzer()
        self.event_bus = event_bus or PerceptionEventBus()

        # Cached states between scheduled intervals
        self._last_detections: List[Detection] = []
        self._last_poses: List[PoseObservation] = []
        self._last_hands: List[HandObservation] = []
        self._known_track_ids: set[int] = set()

    def process_frame(self, packet: FramePacket) -> PerceptionState:
        """Execute one complete perception cycle on an ingested frame packet."""
        t_start = time.perf_counter()

        # Wrap packet as FrameData for interfaces
        frame_data = FrameData(
            frame_id=packet.frame_id,
            image=packet.image,
            timestamp_mono=packet.timestamp_mono,
            timestamp_wall=packet.timestamp_wall,
            source_id=packet.source_id,
        )

        frame_id = packet.frame_id

        # 1. Quality Analysis
        t_q0 = time.perf_counter()
        if self.scheduler.should_run_quality(frame_id):
            quality = self.quality_analyzer.analyze(packet.image)
        else:
            quality = None
        quality_ms = round((time.perf_counter() - t_q0) * 1000.0, 2)

        # 2. Object Detection
        t_d0 = time.perf_counter()
        if self.scheduler.should_run_detection(frame_id):
            detections = self.detector.detect(frame_data)
            self._last_detections = detections
            for det in detections:
                self.event_bus.publish(ObjectDetectedEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, detection=det))
        else:
            detections = list(self._last_detections)
        detection_ms = round((time.perf_counter() - t_d0) * 1000.0, 2)

        # 3. Multi-Object Tracking
        t_t0 = time.perf_counter()
        if self.scheduler.should_run_tracking(frame_id):
            tracks = self.tracker.update(detections, frame_id)
            current_tids = {t.track_id for t in tracks if t.is_active}

            # Emit track lifecycle events
            for t in tracks:
                if t.track_id not in self._known_track_ids:
                    self._known_track_ids.add(t.track_id)
                    self.event_bus.publish(TrackCreatedEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, track=t))

            lost_tids = self._known_track_ids - current_tids
            for lid in lost_tids:
                self._known_track_ids.remove(lid)
                lost_track = next((t for t in tracks if t.track_id == lid), None)
                if lost_track:
                    self.event_bus.publish(TrackLostEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, track=lost_track))
        else:
            tracks = []
        tracking_ms = round((time.perf_counter() - t_t0) * 1000.0, 2)

        # 4. Pose Estimation
        t_p0 = time.perf_counter()
        if self.scheduler.should_run_pose(frame_id):
            poses = self.pose_estimator.estimate(frame_data)
            self._last_poses = poses
            for pose in poses:
                self.event_bus.publish(PoseUpdatedEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, pose=pose))
        else:
            poses = list(self._last_poses)
        pose_ms = round((time.perf_counter() - t_p0) * 1000.0, 2)

        # 5. Hand Detection
        t_h0 = time.perf_counter()
        if self.scheduler.should_run_hands(frame_id):
            try:
                hands = self.hand_detector.detect(frame_data, poses=poses)
            except TypeError:
                hands = self.hand_detector.detect(frame_data)
            self._last_hands = hands
            for hand in hands:
                self.event_bus.publish(HandDetectedEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, hand=hand))
        else:
            hands = list(self._last_hands)
        hand_ms = round((time.perf_counter() - t_h0) * 1000.0, 2)

        total_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        latency = LatencyBreakdown(
            quality_ms=quality_ms,
            detection_ms=detection_ms,
            tracking_ms=tracking_ms,
            pose_ms=pose_ms,
            hand_ms=hand_ms,
            total_ms=total_ms,
        )

        state = PerceptionState(
            timestamp=packet.timestamp_mono,
            frame_id=frame_id,
            source_id=packet.source_id,
            persons=poses,
            frame_width=packet.width,
            frame_height=packet.height,
            objects=detections,
            hands=hands,
            poses=poses,
            tracks=tracks,
            fps=packet.capture_fps,
            quality=quality,
            latency=latency,
        )

        self.event_bus.publish(PerceptionUpdatedEvent(timestamp=packet.timestamp_mono, frame_id=frame_id, state=state))
        return state

    def reset(self) -> None:
        """Reset internal tracking and cached state."""
        self.tracker.reset()
        self._last_detections.clear()
        self._last_poses.clear()
        self._last_hands.clear()
        self._known_track_ids.clear()

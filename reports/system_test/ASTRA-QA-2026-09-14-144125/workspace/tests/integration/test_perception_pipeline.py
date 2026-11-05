"""Integration test for ASTRA-EA Phase 2 Perception Pipeline."""

from datetime import datetime, timezone
import numpy as np
import pytest

from core.camera.ingestion import FramePacket
from core.camera.interface import CameraSource, FrameData
from core.perception.benchmark import PerceptionBenchmark
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.events import (
    ObjectDetectedEvent,
    PerceptionEventBus,
    PerceptionUpdatedEvent,
    TrackCreatedEvent,
)
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.pipeline import PerceptionPipeline
from core.perception.pose.adapter import LightweightPoseEstimator
from core.perception.scheduler import PerceptionScheduler, SchedulerConfig
from core.perception.tracking.tracker import MultiObjectTracker
from core.perception.visualizer import PerceptionVisualizer


class SyntheticCameraSource(CameraSource):
    """Generates synthetic video frames containing moving color boxes."""

    def __init__(self, total_frames: int = 10):
        self.total_frames = total_frames
        self.current = 0
        self._active = False

    def start(self) -> bool:
        self._active = True
        return True

    def stop(self) -> None:
        self._active = False

    def read(self):
        if not self._active or self.current >= self.total_frames:
            return None
        self.current += 1

        img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Shift red box across frames (dx = 4 pixels per frame)
        offset = self.current * 4
        # Red Box (BGR: 0, 0, 255)
        img[100:180, (100 + offset):(180 + offset)] = (0, 0, 255)
        # Yellow Box (BGR: 0, 255, 255)
        img[220:290, 350:420] = (0, 255, 255)

        return FrameData(
            frame_id=self.current,
            image=img,
            timestamp_mono=100.0 + self.current * 0.033,
            timestamp_wall=datetime.now(timezone.utc),
            source_id="synthetic_camera",
        )

    def get_status(self) -> str:
        return "OPEN" if self._active else "CLOSED"

    def get_fps(self) -> float:
        return 30.0

    def get_resolution(self):
        return (640, 480)

    def get_source_id(self) -> str:
        return "synthetic_camera"

    def get_dropped_frames(self) -> int:
        return 0

    @property
    def is_active(self) -> bool:
        return self._active


def test_perception_pipeline_integration():
    """Verify complete perception cycle: Ingestion -> Detection -> Pose -> Hands -> Tracking -> State -> Visualizer."""
    source = SyntheticCameraSource(total_frames=5)
    source.start()

    detector = ColorSpatialObjectDetector(min_area=500.0)
    pose_est = LightweightPoseEstimator()
    hand_det = LightweightHandDetector()
    tracker = MultiObjectTracker(iou_threshold=0.2)
    scheduler = PerceptionScheduler(SchedulerConfig())
    event_bus = PerceptionEventBus()

    # Track published events
    events_received = []
    event_bus.subscribe(ObjectDetectedEvent, lambda e: events_received.append("OBJECT_DETECTED"))
    event_bus.subscribe(TrackCreatedEvent, lambda e: events_received.append("TRACK_CREATED"))
    event_bus.subscribe(PerceptionUpdatedEvent, lambda e: events_received.append("PERCEPTION_UPDATED"))

    pipeline = PerceptionPipeline(
        detector=detector,
        pose_estimator=pose_est,
        hand_detector=hand_det,
        tracker=tracker,
        scheduler=scheduler,
        event_bus=event_bus,
    )

    visualizer = PerceptionVisualizer()

    states = []
    while True:
        fd = source.read()
        if fd is None:
            break
        packet = FramePacket.from_frame_data(fd, capture_fps=30.0)
        state = pipeline.process_frame(packet)
        states.append(state)

        # Render debug visualizer
        rendered = visualizer.render(packet.image, state)
        assert rendered.shape == packet.image.shape

    assert len(states) == 5
    # Verify track identity continuity across frames
    assert len(states[0].tracks) >= 2
    initial_tids = {t.track_id for t in states[0].tracks}
    final_tids = {t.track_id for t in states[-1].tracks}
    # Track IDs should persist across synthetic frames
    assert len(initial_tids.intersection(final_tids)) >= 1

    # Verify event bus received dispatches
    assert "OBJECT_DETECTED" in events_received
    assert "TRACK_CREATED" in events_received
    assert "PERCEPTION_UPDATED" in events_received

    # Verify benchmark runs cleanly on synthetic source
    source2 = SyntheticCameraSource(total_frames=5)
    benchmark = PerceptionBenchmark(pipeline=pipeline, camera_source=source2)
    report = benchmark.run(max_frames=5)
    assert report.total_frames == 5
    assert report.p50_latency_ms >= 0.0
    assert "NOT EVALUATED" in report.accuracy_status

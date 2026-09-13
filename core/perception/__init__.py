"""ASTRA-EA Perception Subsystem.

Provides modular computer vision, pose estimation, hand tracking, and multi-object
tracking for onboard scientific experiment assurance.
"""

from core.perception.benchmark import BenchmarkReport, PerceptionBenchmark
from core.perception.detection.color_adapter import ColorSpatialObjectDetector
from core.perception.detection.interface import ObjectDetector
from core.perception.detection.registry import DatasetMetadata, ModelMetadata, ModelRegistry
from core.perception.detection.yolo_adapter import YOLOAdapter
from core.perception.device import DeviceInfo, DeviceManager
from core.perception.events import (
    FrameCapturedEvent,
    HandDetectedEvent,
    ObjectDetectedEvent,
    ObjectLostEvent,
    PerceptionEvent,
    PerceptionEventBus,
    PerceptionUpdatedEvent,
    PersonDetectedEvent,
    PoseUpdatedEvent,
    TrackCreatedEvent,
    TrackLostEvent,
)
from core.perception.hands.adapter import LightweightHandDetector, StubHandDetector
from core.perception.hands.interface import HandDetector
from core.perception.pipeline import PerceptionPipeline
from core.perception.pose.adapter import LightweightPoseEstimator, StubPoseEstimator
from core.perception.pose.interface import PoseEstimator
from core.perception.quality import FrameQuality, FrameQualityAnalyzer, QualityGrade
from core.perception.scheduler import PerceptionScheduler, SchedulerConfig
from core.perception.tracking.interface import Tracker
from core.perception.tracking.tracker import MultiObjectTracker
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
from core.perception.visualizer import OverlayConfig, PerceptionVisualizer

__all__ = [
    "ObjectDetector",
    "ColorSpatialObjectDetector",
    "YOLOAdapter",
    "ModelRegistry",
    "ModelMetadata",
    "DatasetMetadata",
    "PoseEstimator",
    "LightweightPoseEstimator",
    "StubPoseEstimator",
    "HandDetector",
    "LightweightHandDetector",
    "StubHandDetector",
    "Tracker",
    "MultiObjectTracker",
    "PerceptionPipeline",
    "PerceptionScheduler",
    "SchedulerConfig",
    "DeviceManager",
    "DeviceInfo",
    "FrameQualityAnalyzer",
    "FrameQuality",
    "QualityGrade",
    "PerceptionVisualizer",
    "OverlayConfig",
    "PerceptionEventBus",
    "PerceptionEvent",
    "PerceptionState",
    "Detection",
    "PoseObservation",
    "HandObservation",
    "Track",
    "TrackState",
    "BoundingBox",
    "Keypoint",
    "HandType",
    "LatencyBreakdown",
    "PerceptionBenchmark",
    "BenchmarkReport",
]

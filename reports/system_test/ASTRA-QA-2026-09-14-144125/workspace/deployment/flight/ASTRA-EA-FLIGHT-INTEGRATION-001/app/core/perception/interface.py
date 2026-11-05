"""Abstract interfaces and development stubs for the ASTRA-EA perception tier.

Enforces clean boundaries so concrete deep learning backends (YOLO, MediaPipe, ByteTrack)
can be swapped without affecting downstream interaction or procedure engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.camera.interface import FrameData
from core.perception.types import (
    BoundingBox,
    Detection,
    HandObservation,
    PoseObservation,
    Track,
)


class ObjectDetector(ABC):
    """Abstract interface for scientific experiment object detectors."""

    @abstractmethod
    def detect(self, frame: FrameData) -> List[Detection]:
        """Process video frame and extract 2D object detections."""
        pass


class PoseEstimator(ABC):
    """Abstract interface for astronaut body pose estimation."""

    @abstractmethod
    def estimate(self, frame: FrameData) -> List[PoseObservation]:
        """Extract skeletal joints and body orientation."""
        pass


class HandDetector(ABC):
    """Abstract interface for left and right hand keypoint estimation."""

    @abstractmethod
    def detect(self, frame: FrameData) -> List[HandObservation]:
        """Detect hands and extract wrist/finger landmarks."""
        pass


class Tracker(ABC):
    """Abstract interface for multi-object tracking."""

    @abstractmethod
    def update(self, detections: List[Detection], frame_id: int) -> List[Track]:
        """Associate detections across frames and maintain persistent tracks."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracking states."""
        pass


# ==============================================================================
# DEVELOPMENT STUBS (FOR UNIT & INTEGRATION TESTING ONLY)
# Stubs are strictly labeled with source="STUB" to satisfy the Anti-Fake Rule.
# ==============================================================================


class StubObjectDetector(ObjectDetector):
    """Development double providing deterministic detections for contract tests."""

    def __init__(self, predefined_detections: List[Detection] = None):
        self.predefined = predefined_detections or []

    def detect(self, frame: FrameData) -> List[Detection]:
        results = []
        for d in self.predefined:
            # Ensure source is explicitly marked STUB
            results.append(
                Detection(
                    class_name=d.class_name,
                    confidence=d.confidence,
                    bbox=d.bbox,
                    track_id=d.track_id,
                    timestamp=frame.timestamp_mono,
                    source="STUB",
                )
            )
        return results


class StubTracker(Tracker):
    """Simple centroid-based development tracker for testing contract pipelines."""

    def __init__(self):
        self._next_id = 1
        self._tracks: List[Track] = []

    def update(self, detections: List[Detection], frame_id: int) -> List[Track]:
        updated: List[Track] = []
        for det in detections:
            track = Track(
                track_id=det.track_id or self._next_id,
                class_name=det.class_name,
                bbox=det.bbox,
                confidence=det.confidence,
                history=[det.bbox.center],
            )
            if det.track_id is None:
                self._next_id += 1
            updated.append(track)
        self._tracks = updated
        return self._tracks

    def reset(self) -> None:
        self._next_id = 1
        self._tracks.clear()

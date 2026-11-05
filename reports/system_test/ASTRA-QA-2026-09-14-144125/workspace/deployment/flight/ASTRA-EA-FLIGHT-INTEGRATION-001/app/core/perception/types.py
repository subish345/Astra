"""Standardized data structures for the ASTRA-EA perception tier.

Provides typed containers for 2D bounding boxes, detections, human poses,
hand keypoints, multi-object tracks, frame quality, latency profiles, and
the aggregated PerceptionState.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.perception.quality import FrameQuality


@dataclass
class BoundingBox:
    """Normalized or pixel-space 2D bounding box."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def iou(self, other: BoundingBox) -> float:
        """Compute Intersection-over-Union (IoU) with another bounding box."""
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)

        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        intersection = iw * ih

        union = self.area + other.area - intersection
        if union <= 0.0:
            return 0.0
        return intersection / union


class HandType(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UNKNOWN = "UNKNOWN"


@dataclass
class Keypoint:
    """Individual 2D/3D joint or anatomical landmark."""
    x: float
    y: float
    confidence: float
    z: Optional[float] = None
    name: Optional[str] = None


@dataclass
class Detection:
    """Object detection result for a single entity."""
    class_name: str
    confidence: float
    bbox: BoundingBox
    track_id: Optional[int] = None
    timestamp: float = 0.0
    frame_id: int = 0
    source: str = "LIVE"  # Explicitly 'LIVE', 'SIMULATION', or 'STUB'

    @property
    def center(self) -> Tuple[float, float]:
        return self.bbox.center


@dataclass
class PoseObservation:
    """Estimated body pose of an astronaut."""
    person_id: int
    keypoints: List[Keypoint]
    confidence: float
    bbox: Optional[BoundingBox] = None
    orientation_angle: Optional[float] = None  # Angle relative to vertical
    source: str = "LIVE"

    def get_keypoint(self, name: str) -> Optional[Keypoint]:
        """Fetch landmark by anatomical name."""
        name_lower = name.lower()
        for kp in self.keypoints:
            if kp.name and kp.name.lower() == name_lower:
                return kp
        return None


@dataclass
class HandObservation:
    """Estimated hand and finger keypoint observation."""
    hand_type: HandType
    keypoints: List[Keypoint]
    confidence: float
    wrist: Tuple[float, float]
    bbox: Optional[BoundingBox] = None
    source: str = "LIVE"


class TrackState(str, Enum):
    """Lifecycle states of an object track under potential visual occlusion."""
    VISIBLE = "VISIBLE"
    TEMPORARILY_LOST = "TEMPORARILY_LOST"
    REACQUIRED = "REACQUIRED"
    LOST = "LOST"


@dataclass
class Track:
    """Persistent object or entity track maintained over consecutive frames."""
    track_id: int
    class_name: str
    bbox: BoundingBox
    confidence: float
    velocity: Tuple[float, float] = (0.0, 0.0)
    history: List[Tuple[float, float]] = field(default_factory=list)  # Centroid path history
    age_frames: int = 1
    lost_frames: int = 0
    state: TrackState = TrackState.VISIBLE
    is_active: bool = True

    @property
    def center(self) -> Tuple[float, float]:
        return self.bbox.center


@dataclass
class LatencyBreakdown:
    """Millisecond latency metrics across individual pipeline stages."""
    capture_ms: float = 0.0
    quality_ms: float = 0.0
    detection_ms: float = 0.0
    pose_ms: float = 0.0
    hand_ms: float = 0.0
    tracking_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class PerceptionState:
    """Normalized, frame-synchronized perception state emitted by the pipeline."""
    timestamp: float
    frame_id: int
    source_id: str
    persons: List[PoseObservation] = field(default_factory=list)
    objects: List[Detection] = field(default_factory=list)
    hands: List[HandObservation] = field(default_factory=list)
    poses: List[PoseObservation] = field(default_factory=list)
    tracks: List[Track] = field(default_factory=list)
    fps: float = 0.0
    quality: Optional[FrameQuality] = None
    latency: LatencyBreakdown = field(default_factory=LatencyBreakdown)
    metadata: Dict[str, Any] = field(default_factory=dict)

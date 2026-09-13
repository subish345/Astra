"""Standardized data structures for the ASTRA-EA perception tier.

Provides typed containers for 2D bounding boxes, detections, human poses,
hand keypoints, and multi-object tracks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


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
    source: str = "LIVE"  # Explicitly 'LIVE', 'SIMULATION', or 'STUB'


@dataclass
class PoseObservation:
    """Estimated body pose of an astronaut."""
    person_id: int
    keypoints: List[Keypoint]
    confidence: float
    bbox: Optional[BoundingBox] = None
    orientation_angle: Optional[float] = None  # Angle relative to vertical
    source: str = "LIVE"


@dataclass
class HandObservation:
    """Estimated hand and finger keypoint observation."""
    hand_type: HandType
    keypoints: List[Keypoint]
    confidence: float
    wrist: Tuple[float, float]
    bbox: Optional[BoundingBox] = None
    source: str = "LIVE"


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
    is_active: bool = True

"""Activity recognition data structures for ASTRA-EA.

Represents temporal actions aggregated across sliding observation windows.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from core.interaction.types import InteractionEvent


class PrimitiveActivityType(str, Enum):
    """Fine-grained instantaneous or short-duration physical primitives."""
    IDLE = "IDLE"
    APPROACH = "APPROACH"
    TOUCH = "TOUCH"
    GRASP = "GRASP"
    LIFT = "LIFT"
    HOLD = "HOLD"
    MOVE = "MOVE"
    PLACE = "PLACE"
    RELEASE = "RELEASE"


class CompositeActivityType(str, Enum):
    """High-level task-oriented activity composed of primitive sequences."""
    PICKUP = "PICKUP"
    MOVE_OBJECT = "MOVE_OBJECT"
    PLACE_OBJECT = "PLACE_OBJECT"
    INSPECT_OBJECT = "INSPECT_OBJECT"


class ActivityStatus(str, Enum):
    """Lifecycle status of an ongoing or completed activity."""
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    CONFIRMED = "CONFIRMED"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"
    UNCERTAIN = "UNCERTAIN"


class ActivityConfidenceLevel(str, Enum):
    """Qualitative explainable confidence tier."""
    HIGH = "HIGH"        # >= 0.80
    MEDIUM = "MEDIUM"    # >= 0.60
    LOW = "LOW"          # >= 0.40
    UNKNOWN = "UNKNOWN"  # < 0.40


@dataclass
class TemporalFeatureSet:
    """Kinematic and temporal features extracted over a sliding observation window."""
    position_delta: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    acceleration: Tuple[float, float] = (0.0, 0.0)
    distance_change: float = 0.0
    contact_duration: float = 0.0
    object_displacement: float = 0.0
    hand_object_relative_motion: float = 0.0
    vertical_displacement: float = 0.0
    duration_seconds: float = 0.0


@dataclass
class TemporalWindow:
    """Sliding time window of multi-frame observations."""
    start_time: float
    end_time: float
    interactions: List[InteractionEvent] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


@dataclass
class ActivityObservation:
    """Classified human activity with temporal bounds, confidence score, and evidence trail."""
    activity_name: str
    actor: str
    target_object_id: str
    confidence: float
    window: TemporalWindow
    activity_id: str = field(default_factory=lambda: f"ACT_{uuid.uuid4().hex[:8].upper()}")
    target_track_id: Optional[int] = None
    status: ActivityStatus = ActivityStatus.CONFIRMED
    confidence_level: ActivityConfidenceLevel = ActivityConfidenceLevel.MEDIUM
    primitives: List[str] = field(default_factory=list)
    evidence_refs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def start_time(self) -> float:
        return self.window.start_time

    @property
    def end_time(self) -> float:
        return self.window.end_time

    @property
    def duration_seconds(self) -> float:
        return self.window.duration

    @property
    def activity_type(self) -> str:
        return self.activity_name

    @property
    def target_objects(self) -> List[str]:
        return [self.target_object_id] if self.target_object_id else []

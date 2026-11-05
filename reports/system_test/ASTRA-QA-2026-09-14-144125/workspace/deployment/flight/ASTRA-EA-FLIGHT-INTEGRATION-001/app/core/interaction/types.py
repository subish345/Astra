"""Data structures for hand-object interaction understanding in ASTRA-EA.

Models the progression from hand proximity to physical contact, grasping, motion,
and release.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from core.perception.types import HandType


class InteractionState(str, Enum):
    """Primitive interaction states representing physical coupling."""
    NONE = "NONE"
    APPROACHING = "APPROACHING"
    NEAR = "NEAR"
    CONTACT = "CONTACT"
    GRASPING = "GRASPING"
    HOLDING = "HOLDING"
    MOVING = "MOVING"
    RELEASING = "RELEASING"
    RELEASED = "RELEASED"


@dataclass
class SpatialRelationship:
    """Instantaneous spatial and kinematic relationship between a hand and an object."""
    hand_type: HandType
    target_track_id: int
    target_object_id: str
    pixel_distance: float
    normalized_distance: float
    overlap_iou: float
    relative_quadrant: str  # e.g., "ABOVE", "BELOW", "LEFT", "RIGHT", "INSIDE"
    hand_center: Tuple[float, float]
    object_center: Tuple[float, float]
    hand_velocity: Tuple[float, float] = (0.0, 0.0)
    object_velocity: Tuple[float, float] = (0.0, 0.0)
    relative_velocity: Tuple[float, float] = (0.0, 0.0)
    approach_speed: float = 0.0  # Rate of normalized distance change/sec (negative = approaching)
    motion_correlation: float = 0.0  # Cosine similarity in [-1.0, 1.0] between velocity vectors


@dataclass
class InteractionEvent:
    """Represents an observed physical interaction between a hand and an experiment object."""
    target_object_id: str
    target_track_id: int
    hand_type: HandType
    state: InteractionState
    distance: float  # Normalized Euclidean distance between hand wrist/centroid and object
    confidence: float
    timestamp: float
    interaction_id: str = field(default_factory=lambda: f"INT_{uuid.uuid4().hex[:8].upper()}")
    relative_velocity: Tuple[float, float] = (0.0, 0.0)
    duration_seconds: float = 0.0
    spatial: Optional[SpatialRelationship] = None
    actor: str = "ASTRONAUT"
    is_uncertain: bool = False
    evidence_details: Dict[str, Any] = field(default_factory=dict)

"""Data structures for hand-object interaction understanding in ASTRA-EA.

Models the progression from hand proximity to physical contact, grasping, motion,
and release.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from core.perception.types import HandType


class InteractionState(str, Enum):
    """Primitive interaction states representing physical coupling."""
    NONE = "NONE"
    APPROACHING = "APPROACHING"
    CONTACT = "CONTACT"
    GRASPING = "GRASPING"
    HOLDING = "HOLDING"
    MOVING = "MOVING"
    RELEASING = "RELEASING"
    RELEASED = "RELEASED"


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

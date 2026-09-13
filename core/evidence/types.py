"""Multimodal evidence structures for ASTRA-EA.

This is a core architectural innovation of ASTRA-EA: ensuring that AI confidence
never directly becomes mission ground truth, but is corroborated by explainable evidence factors.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class EvidenceType(str, Enum):
    """Corroborating evidence dimensions required for decision assurance."""
    OBJECT_DETECTED = "OBJECT_DETECTED"
    ASTRONAUT_DETECTED = "ASTRONAUT_DETECTED"
    HAND_DETECTED = "HAND_DETECTED"
    CONTACT_DETECTED = "CONTACT_DETECTED"
    OBJECT_MOTION = "OBJECT_MOTION"
    HAND_MOTION = "HAND_MOTION"
    POSE_CONSISTENT = "POSE_CONSISTENT"
    TEMPORAL_CONSISTENCY = "TEMPORAL_CONSISTENCY"
    SPATIAL_RELATIONSHIP = "SPATIAL_RELATIONSHIP"
    EXPECTED_OBJECT_MATCH = "EXPECTED_OBJECT_MATCH"


@dataclass
class EvidenceItem:
    """Individual evidence factor with pass/fail flag and quantitative confidence."""
    evidence_type: EvidenceType
    verified: bool
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    """Consolidated bundle of explainable evidence supporting a candidate activity."""
    activity_id: str
    activity_name: str
    target_object_id: str
    timestamp: float
    items: Dict[str, EvidenceItem] = field(default_factory=dict)
    evidence_score: float = 0.0  # Normalized composite score [0.0, 1.0]
    is_conclusive: bool = False
    bundle_id: str = field(default_factory=lambda: f"EVD_{uuid.uuid4().hex[:8].upper()}")

    def add_item(self, item: EvidenceItem) -> None:
        self.items[item.evidence_type.value] = item

    def check_requirement(self, requirement_name: str) -> bool:
        """Check whether a required evidence factor is verified."""
        req_upper = requirement_name.upper()
        if req_upper in self.items:
            return self.items[req_upper].verified
        # Fallback to loose naming match
        for k, v in self.items.items():
            if requirement_name.lower() in k.lower():
                return v.verified
        return False

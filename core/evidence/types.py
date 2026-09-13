"""Multimodal evidence structures for ASTRA-EA.

This is a core architectural innovation of ASTRA-EA: ensuring that AI confidence
never directly becomes mission ground truth, but is corroborated by explainable evidence factors.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EvidenceType(str, Enum):
    """Canonical corroborating evidence dimensions required for decision assurance."""
    ACTOR_DETECTED = "ACTOR_DETECTED"
    OBJECT_DETECTED = "OBJECT_DETECTED"
    HAND_DETECTED = "HAND_DETECTED"
    HAND_OBJECT_CONTACT = "HAND_OBJECT_CONTACT"
    CONTACT_CLEARED = "CONTACT_CLEARED"
    OBJECT_MOTION = "OBJECT_MOTION"
    HAND_MOTION = "HAND_MOTION"
    COUPLED_MOTION = "COUPLED_MOTION"
    SPATIAL_PROXIMITY = "SPATIAL_PROXIMITY"
    DESTINATION_MATCH = "DESTINATION_MATCH"
    OBJECT_STABILIZED = "OBJECT_STABILIZED"
    TEMPORAL_PRESENCE = "TEMPORAL_PRESENCE"
    TEMPORAL_CONSISTENCY = "TEMPORAL_CONSISTENCY"
    POSE_CONSISTENCY = "POSE_CONSISTENCY"
    ACTIVITY_CONFIRMED = "ACTIVITY_CONFIRMED"
    PROCEDURE_MATCH = "PROCEDURE_MATCH"


CANONICAL_EVIDENCE_MAP: Dict[str, str] = {
    # Actor aliases
    "ASTRONAUT_VISIBLE": "ACTOR_DETECTED",
    "ASTRONAUT_DETECTED": "ACTOR_DETECTED",
    "PERSON_DETECTED": "ACTOR_DETECTED",
    "PERSON_VISIBLE": "ACTOR_DETECTED",
    # Object aliases
    "OBJECT_VISIBLE": "OBJECT_DETECTED",
    "TARGET_OBJECT_DETECTED": "OBJECT_DETECTED",
    # Hand aliases
    "HAND_VISIBLE": "HAND_DETECTED",
    # Contact aliases
    "CONTACT_DETECTED": "HAND_OBJECT_CONTACT",
    "HAND_CONTACT": "HAND_OBJECT_CONTACT",
    # Motion aliases
    "MOTION_COUPLED": "COUPLED_MOTION",
    "OBJECT_MOVING": "OBJECT_MOTION",
    # Proximity aliases
    "PROXIMITY": "SPATIAL_PROXIMITY",
    "STATION_PROXIMITY": "SPATIAL_PROXIMITY",
    "APPROACH_CONFIRMED": "SPATIAL_PROXIMITY",
    # Destination & Stabilization aliases
    "DESTINATION_REACHED": "DESTINATION_MATCH",
    "SURFACE_REACHED": "DESTINATION_MATCH",
    "OBJECT_STABLE": "OBJECT_STABILIZED",
    "STABILIZED": "OBJECT_STABILIZED",
    # Clearance aliases
    "RELEASED": "CONTACT_CLEARED",
    "HAND_RELEASED": "CONTACT_CLEARED",
    # Pose / Temporal aliases
    "POSE_CONSISTENT": "POSE_CONSISTENCY",
    "TEMPORAL_CONSISTENT": "TEMPORAL_CONSISTENCY",
    "PRESENCE_CONFIRMED": "TEMPORAL_PRESENCE",
}


def normalize_evidence_name(name: str) -> str:
    """Normalize any raw evidence name or legacy alias to its canonical EvidenceType value."""
    key = name.strip().upper().replace(" ", "_").replace("-", "_")
    return CANONICAL_EVIDENCE_MAP.get(key, key)


@dataclass
class EvidenceItem:
    """Individual evidence factor with pass/fail flag and quantitative confidence."""
    evidence_type: EvidenceType
    verified: bool
    confidence: float
    object_id: Optional[str] = None
    hand_id: Optional[str] = None
    start_frame: Optional[int] = None
    end_frame: Optional[int] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.evidence_type.value,
            "verified": self.verified,
            "confidence": round(self.confidence, 3),
            "object_id": self.object_id,
            "hand_id": self.hand_id,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "start_time": round(self.start_time, 3) if self.start_time is not None else None,
            "end_time": round(self.end_time, 3) if self.end_time is not None else None,
            "details": self.details,
        }


@dataclass
class EvidenceBundle:
    """Consolidated bundle of explainable evidence supporting a candidate activity or step."""
    activity_id: str = ""
    activity_name: str = ""
    target_object_id: Optional[str] = None
    timestamp: float = 0.0
    step_id: Optional[str] = None
    items: Dict[str, EvidenceItem] = field(default_factory=dict)
    required_satisfied: bool = False
    optional_satisfied: bool = False
    missing_required: List[str] = field(default_factory=list)
    evidence_score: float = 0.0  # Normalized composite score [0.0, 1.0]
    confidence: float = 0.0
    is_conclusive: bool = False
    timestamp_range: Tuple[float, float] = (0.0, 0.0)
    source_frames: List[int] = field(default_factory=list)
    bundle_id: str = field(default_factory=lambda: f"EVD_{uuid.uuid4().hex[:8].upper()}")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.confidence == 0.0 and self.evidence_score > 0.0:
            self.confidence = self.evidence_score
        elif self.evidence_score == 0.0 and self.confidence > 0.0:
            self.evidence_score = self.confidence

    def add_item(self, item: EvidenceItem) -> None:
        self.items[item.evidence_type.value] = item
        if item.start_frame is not None and item.start_frame not in self.source_frames:
            self.source_frames.append(item.start_frame)
        if item.end_frame is not None and item.end_frame not in self.source_frames:
            self.source_frames.append(item.end_frame)

    def check_requirement(self, requirement_name: str) -> bool:
        """Check whether a required evidence factor is verified, resolving any legacy aliases."""
        canonical = normalize_evidence_name(requirement_name)

        # Direct canonical lookup
        if canonical in self.items:
            return self.items[canonical].verified

        # Raw lookup
        raw_upper = requirement_name.strip().upper().replace(" ", "_")
        if raw_upper in self.items:
            return self.items[raw_upper].verified

        # Substring search fallback
        req_clean = requirement_name.lower().replace("_", "")
        for k, v in self.items.items():
            if req_clean in k.lower().replace("_", ""):
                return v.verified
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bundle_id": self.bundle_id,
            "step_id": self.step_id,
            "activity_id": self.activity_id,
            "activity_name": self.activity_name,
            "target_object_id": self.target_object_id,
            "timestamp": round(self.timestamp, 3),
            "evidence_score": round(self.evidence_score, 3),
            "confidence": round(self.confidence, 3),
            "required_satisfied": self.required_satisfied,
            "optional_satisfied": self.optional_satisfied,
            "missing_required": self.missing_required,
            "is_conclusive": self.is_conclusive,
            "timestamp_range": [round(t, 3) for t in self.timestamp_range],
            "source_frames": self.source_frames,
            "items": {k: v.to_dict() for k, v in self.items.items()},
        }

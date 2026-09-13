# ==============================================================================
# ASTRA-EA Assurance Decision Structures
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Assurance decision structures for ASTRA-EA.

Enforces the three core mission states: VERIFIED, UNCERTAIN, and DEVIATION,
carrying camera profile metadata and closed-loop recovery guidance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.mission.events import DecisionType, DeviationReason


@dataclass
class AssuranceDecision:
    """Evaluation result produced by the procedure assurance engine."""

    experiment_id: str
    step_id: str
    sequence: int
    decision: DecisionType
    confidence: float
    deviation_reason: Optional[DeviationReason] = None
    reason: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: f"DEC_{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    camera_profile: str = "VIEW_LEFT"
    session_id: str = "SESSION_001"
    procedure_version: str = "1.0.0"
    recommended_recovery: Optional[str] = None
    severity: Optional[str] = None

    @property
    def is_verified(self) -> bool:
        return self.decision == DecisionType.VERIFIED

    @property
    def is_uncertain(self) -> bool:
        return self.decision == DecisionType.UNCERTAIN

    @property
    def is_deviation(self) -> bool:
        return self.decision == DecisionType.DEVIATION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "experiment_id": self.experiment_id,
            "session_id": self.session_id,
            "camera_profile": self.camera_profile,
            "step_id": self.step_id,
            "sequence": self.sequence,
            "decision": self.decision.value if hasattr(self.decision, "value") else str(self.decision),
            "confidence": float(self.confidence),
            "deviation_reason": (
                self.deviation_reason.value
                if self.deviation_reason and hasattr(self.deviation_reason, "value")
                else (str(self.deviation_reason) if self.deviation_reason else None)
            ),
            "reason": self.reason or (self.reasons[0] if self.reasons else ""),
            "reasons": self.reasons,
            "evidence_summary": self.evidence_summary,
            "recommended_recovery": self.recommended_recovery,
            "severity": self.severity,
            "procedure_version": self.procedure_version,
            "timestamp": self.timestamp.isoformat(),
        }

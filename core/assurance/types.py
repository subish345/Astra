"""Assurance decision structures for ASTRA-EA.

Enforces the three core mission states: VERIFIED, UNCERTAIN, and DEVIATION.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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
    evidence_summary: Dict[str, Any] = field(default_factory=dict)
    decision_id: str = field(default_factory=lambda: f"DEC_{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_verified(self) -> bool:
        return self.decision == DecisionType.VERIFIED

    @property
    def is_uncertain(self) -> bool:
        return self.decision == DecisionType.UNCERTAIN

    @property
    def is_deviation(self) -> bool:
        return self.decision == DecisionType.DEVIATION

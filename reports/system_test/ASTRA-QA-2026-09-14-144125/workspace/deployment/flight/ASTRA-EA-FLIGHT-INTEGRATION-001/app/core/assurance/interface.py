"""Abstract interface and test stubs for the ASTRA-EA assurance engine.

Determines whether observed evidence validates procedural progress or signals a deviation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.activity.types import ActivityObservation
from core.assurance.types import AssuranceDecision, DecisionType
from core.evidence.types import EvidenceBundle
from core.procedure.schema import ExperimentStep


class AssuranceEngine(ABC):
    """Abstract interface for procedural assurance evaluation."""

    @abstractmethod
    def evaluate_step(
        self,
        current_step: ExperimentStep,
        activity: ActivityObservation,
        evidence: EvidenceBundle,
    ) -> AssuranceDecision:
        """Compare observed activity and evidence against expected step parameters."""
        pass


class StubAssuranceEngine(AssuranceEngine):
    """Development stub returning deterministic assurance decisions for testing."""

    def __init__(self, predefined_decision: AssuranceDecision = None):
        self.predefined = predefined_decision

    def evaluate_step(
        self,
        current_step: ExperimentStep,
        activity: ActivityObservation,
        evidence: EvidenceBundle,
    ) -> AssuranceDecision:
        if self.predefined:
            return self.predefined
        return AssuranceDecision(
            experiment_id="DEMO_EXP_001",
            step_id=current_step.id,
            sequence=current_step.sequence,
            decision=DecisionType.VERIFIED,
            confidence=0.90,
            reason="Contract stub verification",
        )

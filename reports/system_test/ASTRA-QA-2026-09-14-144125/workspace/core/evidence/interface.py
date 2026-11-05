"""Abstract interface and test stubs for the ASTRA-EA evidence engine.

Computes explainable multi-factor evidence bundles for candidate activities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.activity.types import ActivityObservation
from core.evidence.types import EvidenceBundle
from core.interaction.types import InteractionEvent
from core.perception.types import Track


class EvidenceEngine(ABC):
    """Abstract interface for multi-factor evidence evaluation."""

    @abstractmethod
    def evaluate(
        self,
        activity: ActivityObservation,
        interactions: List[InteractionEvent],
        tracks: List[Track],
    ) -> EvidenceBundle:
        """Construct an explainable EvidenceBundle for a candidate activity."""
        pass


class StubEvidenceEngine(EvidenceEngine):
    """Development stub returning configured evidence bundles for testing."""

    def __init__(self, predefined_bundle: EvidenceBundle = None):
        self.predefined = predefined_bundle

    def evaluate(
        self,
        activity: ActivityObservation,
        interactions: List[InteractionEvent],
        tracks: List[Track],
    ) -> EvidenceBundle:
        if self.predefined:
            return self.predefined
        return EvidenceBundle(
            activity_id=activity.activity_id,
            activity_name=activity.activity_name,
            target_object_id=activity.target_object_id,
            timestamp=activity.end_time,
            evidence_score=0.85,
            is_conclusive=True,
        )

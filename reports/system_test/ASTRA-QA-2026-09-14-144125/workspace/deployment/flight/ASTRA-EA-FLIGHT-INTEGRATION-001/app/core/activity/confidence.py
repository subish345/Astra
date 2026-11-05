"""Explainable multi-signal confidence engine and uncertainty handler for physical activities.

Aggregates object detection, hand localization, contact persistence, motion coupling,
and temporal consistency into an explainable composite score and qualitative confidence tier.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from core.activity.types import ActivityConfidenceLevel, ActivityStatus, TemporalFeatureSet
from core.common.config import ActivitySettings
from core.interaction.types import InteractionEvent, InteractionState


class ActivityConfidenceEngine:
    """Calculates explainable confidence scores and assigns uncertainty status."""

    def __init__(self, settings: Optional[ActivitySettings] = None):
        self.cfg = settings or ActivitySettings()

    def calculate_confidence(
        self,
        event: InteractionEvent,
        features: TemporalFeatureSet,
        hand_confidence: float = 0.85,
        object_confidence: float = 0.90,
    ) -> Tuple[float, ActivityConfidenceLevel, Dict[str, Any]]:
        """Compute weighted evidence score and qualitative tier.

        Formula (Calibration Baseline):
            C = w_obj * C_obj + w_hand * C_hand + w_cont * C_cont + w_mot * C_mot + w_temp * C_temp
        """
        # 1. Contact score
        if event.state in (InteractionState.CONTACT, InteractionState.GRASPING, InteractionState.HOLDING, InteractionState.MOVING):
            contact_score = min(1.0, 0.60 + 0.40 * min(1.0, features.contact_duration / 0.5))
        elif event.state in (InteractionState.APPROACHING, InteractionState.NEAR):
            contact_score = 0.50
        elif event.state in (InteractionState.RELEASING, InteractionState.RELEASED):
            contact_score = 0.75
        else:
            contact_score = 0.10

        # 2. Motion coupling score
        if event.state == InteractionState.MOVING:
            motion_score = max(0.0, features.hand_object_relative_motion)
        elif event.state in (InteractionState.HOLDING, InteractionState.CONTACT):
            motion_score = 0.80 if features.object_displacement < 25.0 else 0.50
        else:
            motion_score = 0.60

        # 3. Temporal consistency score
        temporal_score = min(1.0, features.duration_seconds / max(0.1, self.cfg.min_activity_duration_seconds))

        # 4. Weighted combination
        raw_score = (
            (self.cfg.confidence_weight_object * object_confidence)
            + (self.cfg.confidence_weight_hand * hand_confidence)
            + (self.cfg.confidence_weight_contact * contact_score)
            + (self.cfg.confidence_weight_motion * motion_score)
            + (self.cfg.confidence_weight_temporal * temporal_score)
        )
        final_score = round(max(0.0, min(1.0, raw_score)), 3)

        # 5. Qualitative level mapping
        if final_score >= 0.80:
            level = ActivityConfidenceLevel.HIGH
        elif final_score >= 0.60:
            level = ActivityConfidenceLevel.MEDIUM
        elif final_score >= 0.40:
            level = ActivityConfidenceLevel.LOW
        else:
            level = ActivityConfidenceLevel.UNKNOWN

        breakdown = {
            "object_confidence": round(object_confidence, 2),
            "hand_confidence": round(hand_confidence, 2),
            "contact_score": round(contact_score, 2),
            "motion_score": round(motion_score, 2),
            "temporal_score": round(temporal_score, 2),
            "final_score": final_score,
            "weights": {
                "w_object": self.cfg.confidence_weight_object,
                "w_hand": self.cfg.confidence_weight_hand,
                "w_contact": self.cfg.confidence_weight_contact,
                "w_motion": self.cfg.confidence_weight_motion,
                "w_temporal": self.cfg.confidence_weight_temporal,
            },
        }

        return final_score, level, breakdown

    def resolve_status(
        self,
        event: InteractionEvent,
        features: TemporalFeatureSet,
        confidence: float,
    ) -> ActivityStatus:
        """Determine lifecycle status (CONFIRMED, UNCERTAIN, IN_PROGRESS, CANCELLED, ENDED)."""
        if event.is_uncertain:
            return ActivityStatus.UNCERTAIN

        if event.state in (InteractionState.RELEASED, InteractionState.NONE):
            return ActivityStatus.ENDED

        if features.duration_seconds < self.cfg.min_activity_duration_seconds:
            return ActivityStatus.IN_PROGRESS

        if confidence >= 0.60:
            return ActivityStatus.CONFIRMED

        return ActivityStatus.UNCERTAIN

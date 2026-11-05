"""Primitive activity recognition engine consuming temporal features and interaction events.

Recognizes fine-grained physical actions:
IDLE, APPROACH, TOUCH, GRASP, LIFT, HOLD, MOVE, PLACE, RELEASE.
"""

from __future__ import annotations

from typing import List, Optional
from core.activity.confidence import ActivityConfidenceEngine
from core.activity.temporal import TemporalBuffer, TemporalFeatureExtractor
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityObservation,
    ActivityStatus,
    PrimitiveActivityType,
    TemporalWindow,
)
from core.common.config import ActivitySettings
from core.interaction.types import InteractionEvent, InteractionState


class PrimitiveActivityEngine:
    """Evaluates multi-frame temporal features to classify primitive physical actions."""

    def __init__(
        self,
        settings: Optional[ActivitySettings] = None,
        confidence_engine: Optional[ActivityConfidenceEngine] = None,
    ):
        self.cfg = settings or ActivitySettings()
        self.conf_engine = confidence_engine or ActivityConfidenceEngine(self.cfg)

    def evaluate(
        self,
        event: InteractionEvent,
        temporal_buffer: TemporalBuffer,
    ) -> ActivityObservation:
        """Classify the instantaneous primitive activity for an interaction event."""
        hand_type_str = event.hand_type.value if hasattr(event.hand_type, "value") else str(event.hand_type)
        history = temporal_buffer.get_interaction_history(hand_type_str, event.target_track_id)
        trajectory = temporal_buffer.get_track_trajectory(event.target_track_id)

        features = TemporalFeatureExtractor.extract_features(history, trajectory)
        confidence, conf_level, breakdown = self.conf_engine.calculate_confidence(event, features)
        status = self.conf_engine.resolve_status(event, features, confidence)

        # 1. State-to-Primitive mapping logic
        activity_type = PrimitiveActivityType.IDLE

        if event.state == InteractionState.APPROACHING:
            activity_type = PrimitiveActivityType.APPROACH
        elif event.state == InteractionState.NEAR:
            activity_type = PrimitiveActivityType.APPROACH
        elif event.state == InteractionState.CONTACT:
            activity_type = PrimitiveActivityType.TOUCH
        elif event.state == InteractionState.GRASPING:
            activity_type = PrimitiveActivityType.GRASP
        elif event.state == InteractionState.HOLDING:
            activity_type = PrimitiveActivityType.HOLD
        elif event.state == InteractionState.MOVING:
            # Distinguish LIFT (predominantly upward: dy negative) from general horizontal MOVE
            dx, dy = features.position_delta
            if dy < -30.0 and abs(dy) > abs(dx) * 1.2:
                activity_type = PrimitiveActivityType.LIFT
            else:
                activity_type = PrimitiveActivityType.MOVE
        elif event.state == InteractionState.RELEASING:
            # If stationary at release point, consider PLACE
            if features.object_displacement > 20.0 and features.velocity[0] < 15.0 and features.velocity[1] < 15.0:
                activity_type = PrimitiveActivityType.PLACE
            else:
                activity_type = PrimitiveActivityType.RELEASE
        elif event.state == InteractionState.RELEASED:
            activity_type = PrimitiveActivityType.RELEASE
        else:
            activity_type = PrimitiveActivityType.IDLE

        # Construct TemporalWindow snapshot
        window = TemporalWindow(
            start_time=history[0].timestamp if history else event.timestamp,
            end_time=event.timestamp,
            interactions=list(history),
        )

        return ActivityObservation(
            activity_name=activity_type.value,
            actor=event.actor,
            target_object_id=event.target_object_id,
            target_track_id=event.target_track_id,
            confidence=confidence,
            window=window,
            status=status,
            confidence_level=conf_level,
            primitives=[activity_type.value],
            evidence_refs={
                "features": features.__dict__,
                "breakdown": breakdown,
                "interaction_state": event.state.value,
            },
        )

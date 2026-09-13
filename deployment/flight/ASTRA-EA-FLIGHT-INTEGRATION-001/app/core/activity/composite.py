"""Composite activity engine recognizing task-level human workflows.

Aggregates sequences of primitive activities into composite actions:
- GRASP + LIFT -> PICKUP
- HOLD + MOVE -> MOVE_OBJECT
- MOVE + PLACE + RELEASE -> PLACE_OBJECT
Preserving underlying primitive evidence for auditability and verification.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityObservation,
    ActivityStatus,
    CompositeActivityType,
    PrimitiveActivityType,
    TemporalWindow,
)
from core.common.logging import get_logger

logger = get_logger("ACTIVITY")


class CompositeActivityEngine:
    """Statefully composes atomic primitive action traces into higher-level activities."""

    def __init__(self, max_history_per_target: int = 15):
        self.max_history_per_target = max_history_per_target
        # Key: (actor, target_track_id) -> List of recent primitive ActivityObservations
        self._primitive_history: Dict[Tuple[str, int], List[ActivityObservation]] = {}

    def update(self, primitive_obs: ActivityObservation) -> Optional[ActivityObservation]:
        """Incorporate a new primitive observation and check for composite activity formation."""
        key = (primitive_obs.actor, primitive_obs.target_track_id or 0)
        if key not in self._primitive_history:
            self._primitive_history[key] = []

        history = self._primitive_history[key]
        history.append(primitive_obs)
        if len(history) > self.max_history_per_target:
            history.pop(0)

        # Extract sequence of activity names
        recent_primitives = [obs.activity_name for obs in history]

        # 1. Evaluate PICKUP: [APPROACH, TOUCH/GRASP, LIFT]
        if self._matches_pickup(recent_primitives):
            return self._build_composite(
                composite_type=CompositeActivityType.PICKUP,
                history=history,
                latest_obs=primitive_obs,
            )

        # 2. Evaluate MOVE_OBJECT: [HOLD, MOVE] or continuous coupled MOVE
        if self._matches_move(recent_primitives):
            return self._build_composite(
                composite_type=CompositeActivityType.MOVE_OBJECT,
                history=history,
                latest_obs=primitive_obs,
            )

        # 3. Evaluate PLACE_OBJECT: [MOVE, PLACE, RELEASE] or [MOVE, RELEASE]
        if self._matches_place(recent_primitives):
            return self._build_composite(
                composite_type=CompositeActivityType.PLACE_OBJECT,
                history=history,
                latest_obs=primitive_obs,
            )

        return None

    def _matches_pickup(self, seq: List[str]) -> bool:
        """Check whether sequence terminates in a LIFT with preceding GRASP/TOUCH."""
        if not seq or seq[-1] != PrimitiveActivityType.LIFT.value:
            return False
        # Look backwards for GRASP or TOUCH
        has_grasp = any(
            act in (PrimitiveActivityType.GRASP.value, PrimitiveActivityType.TOUCH.value)
            for act in seq[:-1]
        )
        return has_grasp

    def _matches_move(self, seq: List[str]) -> bool:
        """Check whether sequence contains MOVE with preceding HOLD or GRASP."""
        if not seq or seq[-1] != PrimitiveActivityType.MOVE.value:
            return False
        has_hold_or_grasp = any(
            act in (PrimitiveActivityType.HOLD.value, PrimitiveActivityType.GRASP.value)
            for act in seq[:-1]
        )
        # Also match sustained MOVE
        consecutive_moves = sum(1 for act in seq[-3:] if act == PrimitiveActivityType.MOVE.value)
        return has_hold_or_grasp or consecutive_moves >= 2

    def _matches_place(self, seq: List[str]) -> bool:
        """Check whether sequence terminates in RELEASE with preceding MOVE or PLACE."""
        if not seq or seq[-1] not in (PrimitiveActivityType.RELEASE.value, PrimitiveActivityType.PLACE.value):
            return False
        has_move = any(act == PrimitiveActivityType.MOVE.value for act in seq[:-1])
        return has_move

    def _build_composite(
        self,
        composite_type: CompositeActivityType,
        history: List[ActivityObservation],
        latest_obs: ActivityObservation,
    ) -> ActivityObservation:
        """Create composite observation aggregating constituent primitive evidence."""
        start_time = history[0].start_time
        end_time = latest_obs.end_time
        all_interactions = [ev for obs in history for ev in obs.window.interactions]

        # Calculate average confidence across constituent primitives
        mean_conf = round(sum(obs.confidence for obs in history) / len(history), 3)
        if mean_conf >= 0.80:
            tier = ActivityConfidenceLevel.HIGH
        elif mean_conf >= 0.60:
            tier = ActivityConfidenceLevel.MEDIUM
        else:
            tier = ActivityConfidenceLevel.LOW

        primitives_trace = [obs.activity_name for obs in history]

        return ActivityObservation(
            activity_name=composite_type.value,
            actor=latest_obs.actor,
            target_object_id=latest_obs.target_object_id,
            target_track_id=latest_obs.target_track_id,
            confidence=mean_conf,
            window=TemporalWindow(start_time, end_time, all_interactions),
            status=ActivityStatus.CONFIRMED,
            confidence_level=tier,
            primitives=primitives_trace,
            evidence_refs={
                "primitive_count": len(history),
                "constituent_primitives": primitives_trace,
                "composite_rule": f"Rule_{composite_type.value}",
            },
        )

    def reset(self) -> None:
        """Clear historical traces."""
        self._primitive_history.clear()

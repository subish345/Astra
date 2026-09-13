"""State machine managing hand-object physical interaction lifecycles.

Tracks the progression:
NONE -> APPROACHING -> NEAR -> CONTACT -> GRASPING -> HOLDING -> MOVING -> RELEASING -> RELEASED -> NONE
with multi-frame confirmation hysteresis and track loss / occlusion handling.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from core.common.config import InteractionSettings
from core.common.logging import get_logger
from core.interaction.rules import InteractionRules
from core.interaction.types import InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import TrackState

logger = get_logger("INTERACTION")


class HandObjectStateMachine:
    """Stateful tracker for an individual (hand_type, target_track_id) pair."""

    def __init__(
        self,
        hand_type: str,
        target_track_id: int,
        target_object_id: str,
        settings: Optional[InteractionSettings] = None,
    ):
        self.hand_type = hand_type
        self.target_track_id = target_track_id
        self.target_object_id = target_object_id
        self.cfg = settings or InteractionSettings()
        self.rules = InteractionRules(self.cfg)

        self.current_state = InteractionState.NONE
        self.state_start_time = 0.0
        self.last_update_time = 0.0
        self.is_uncertain = False
        self.lost_frames_count = 0

        # Confirmation hysteresis counters
        self.consecutive_contact_frames = 0
        self.consecutive_approach_frames = 0
        self.consecutive_motion_frames = 0
        self.consecutive_release_frames = 0

        # History buffers
        self.recent_distances: List[float] = []
        self.max_history_len = 10

    @property
    def duration_in_state(self) -> float:
        if self.state_start_time <= 0.0:
            return 0.0
        return max(0.0, self.last_update_time - self.state_start_time)

    def transition_to(self, new_state: InteractionState, timestamp: float, reason: str = "") -> None:
        """Execute a state transition and reset appropriate counters."""
        if new_state != self.current_state:
            logger.debug(
                "Interaction [%s <-> %s#%d] %s -> %s (Reason: %s)",
                self.hand_type,
                self.target_object_id,
                self.target_track_id,
                self.current_state.value,
                new_state.value,
                reason,
            )
            self.current_state = new_state
            self.state_start_time = timestamp

    def update(
        self,
        spatial: SpatialRelationship,
        track_state: TrackState,
        timestamp: float,
    ) -> InteractionEvent:
        """Update the state machine given new spatial-kinematic observation."""
        self.last_update_time = timestamp

        # Record normalized distance history
        self.recent_distances.append(spatial.normalized_distance)
        if len(self.recent_distances) > self.max_history_len:
            self.recent_distances.pop(0)

        # 1. Handle visual occlusion or track loss
        if track_state == TrackState.TEMPORARILY_LOST:
            self.lost_frames_count += 1
            self.is_uncertain = True
            if self.lost_frames_count > self.cfg.max_temporary_lost_frames:
                self.transition_to(InteractionState.NONE, timestamp, "Track lost exceeded timeout")
            return self._build_event(spatial, confidence=0.40)
        elif track_state == TrackState.LOST:
            self.transition_to(InteractionState.NONE, timestamp, "Track permanently lost")
            return self._build_event(spatial, confidence=0.0)
        else:
            self.lost_frames_count = 0
            self.is_uncertain = False

        # 2. Evaluate state transitions
        prev_state = self.current_state

        if self.current_state == InteractionState.NONE:
            appr_res = self.rules.evaluate_approach(spatial, self.recent_distances)
            near_res = self.rules.evaluate_near(spatial)
            cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)

            if cont_res.is_triggered:
                self.consecutive_contact_frames += 1
                if self.consecutive_contact_frames >= self.cfg.contact_confirmation_frames:
                    self.transition_to(InteractionState.CONTACT, timestamp, cont_res.reason)
                else:
                    self.transition_to(InteractionState.NEAR, timestamp, "Initial contact in progress")
            elif near_res.is_triggered:
                self.consecutive_contact_frames = 0
                self.transition_to(InteractionState.NEAR, timestamp, near_res.reason)
            elif appr_res.is_triggered:
                self.consecutive_contact_frames = 0
                self.consecutive_approach_frames += 1
                if self.consecutive_approach_frames >= 2:
                    self.transition_to(InteractionState.APPROACHING, timestamp, appr_res.reason)

        elif self.current_state == InteractionState.APPROACHING:
            cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)
            near_res = self.rules.evaluate_near(spatial)
            appr_res = self.rules.evaluate_approach(spatial, self.recent_distances)

            if cont_res.is_triggered:
                self.consecutive_contact_frames += 1
                if self.consecutive_contact_frames >= self.cfg.contact_confirmation_frames:
                    self.transition_to(InteractionState.CONTACT, timestamp, cont_res.reason)
                else:
                    self.transition_to(InteractionState.NEAR, timestamp, "Contact imminent")
            elif near_res.is_triggered:
                self.consecutive_contact_frames = 0
                self.transition_to(InteractionState.NEAR, timestamp, near_res.reason)
            elif not appr_res.is_triggered:
                # Approach aborted or hand moved away
                if spatial.normalized_distance > self.cfg.approach_distance_threshold:
                    self.transition_to(InteractionState.NONE, timestamp, "Distance exceeded approach limit")

        elif self.current_state == InteractionState.NEAR:
            cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)
            if cont_res.is_triggered:
                self.consecutive_contact_frames += 1
                if self.consecutive_contact_frames >= self.cfg.contact_confirmation_frames:
                    self.transition_to(InteractionState.CONTACT, timestamp, cont_res.reason)
            else:
                self.consecutive_contact_frames = 0
                near_res = self.rules.evaluate_near(spatial)
                if not near_res.is_triggered:
                    if spatial.normalized_distance > self.cfg.approach_distance_threshold:
                        self.transition_to(InteractionState.NONE, timestamp, "Departed near zone")
                    else:
                        self.transition_to(InteractionState.APPROACHING, timestamp, "Re-evaluating distance")

        elif self.current_state == InteractionState.CONTACT:
            # Check for grasp / coupled motion vs release vs loss
            rel_res = self.rules.evaluate_release(spatial, prior_state_was_holding_or_moving=False)
            cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)
            motion_res = self.rules.evaluate_coupled_motion(spatial)

            if not cont_res.is_triggered:
                self.consecutive_release_frames += 1
                if self.consecutive_release_frames >= 2:
                    self.transition_to(InteractionState.RELEASED, timestamp, "Contact broken")
            elif motion_res.is_triggered:
                self.consecutive_release_frames = 0
                self.consecutive_motion_frames += 1
                if self.consecutive_motion_frames >= 2:
                    self.transition_to(InteractionState.MOVING, timestamp, motion_res.reason)
                else:
                    self.transition_to(InteractionState.GRASPING, timestamp, "Coupled motion initiated")
            else:
                self.consecutive_release_frames = 0
                # If contact maintained steadily for > 0.3s, promote to GRASPING/HOLDING
                if self.duration_in_state > 0.30:
                    self.transition_to(InteractionState.HOLDING, timestamp, "Persistent stable contact")

        elif self.current_state == InteractionState.GRASPING:
            motion_res = self.rules.evaluate_coupled_motion(spatial)
            cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)

            if not cont_res.is_triggered:
                self.transition_to(InteractionState.RELEASING, timestamp, "Contact broken while grasping")
            elif motion_res.is_triggered:
                self.transition_to(InteractionState.MOVING, timestamp, motion_res.reason)
            elif self.duration_in_state > 0.20:
                self.transition_to(InteractionState.HOLDING, timestamp, "Grasp established into steady hold")

        elif self.current_state == InteractionState.HOLDING:
            motion_res = self.rules.evaluate_coupled_motion(spatial)
            rel_res = self.rules.evaluate_release(spatial, prior_state_was_holding_or_moving=True)

            if rel_res.is_triggered:
                self.transition_to(InteractionState.RELEASING, timestamp, rel_res.reason)
            elif motion_res.is_triggered:
                self.transition_to(InteractionState.MOVING, timestamp, motion_res.reason)

        elif self.current_state == InteractionState.MOVING:
            motion_res = self.rules.evaluate_coupled_motion(spatial)
            rel_res = self.rules.evaluate_release(spatial, prior_state_was_holding_or_moving=True)

            if rel_res.is_triggered:
                self.transition_to(InteractionState.RELEASING, timestamp, rel_res.reason)
            elif not motion_res.is_triggered:
                # Coupled motion ceased, object stationary while contact maintained
                cont_res = self.rules.evaluate_contact(spatial, self.consecutive_contact_frames)
                if cont_res.is_triggered:
                    self.transition_to(InteractionState.HOLDING, timestamp, "Motion stopped, holding continued")
                else:
                    self.transition_to(InteractionState.RELEASING, timestamp, "Motion ceased and contact lost")

        elif self.current_state == InteractionState.RELEASING:
            self.transition_to(InteractionState.RELEASED, timestamp, "Release completed")

        elif self.current_state == InteractionState.RELEASED:
            # Transition back to NONE after 1 frame
            self.transition_to(InteractionState.NONE, timestamp, "Interaction cycle completed")

        confidence = self._compute_state_confidence(spatial)
        return self._build_event(spatial, confidence=confidence)

    def _compute_state_confidence(self, spatial: SpatialRelationship) -> float:
        """Derive explainable confidence for the current interaction state."""
        if self.current_state == InteractionState.NONE:
            return 0.90
        elif self.current_state in (InteractionState.APPROACHING, InteractionState.NEAR):
            return min(0.92, round(0.50 + 0.40 * (1.0 - min(1.0, spatial.normalized_distance)), 2))
        elif self.current_state == InteractionState.CONTACT:
            pers = min(5, self.consecutive_contact_frames) / 5.0
            return round(0.65 + 0.30 * pers, 2)
        elif self.current_state in (InteractionState.GRASPING, InteractionState.HOLDING):
            return 0.85
        elif self.current_state == InteractionState.MOVING:
            corr = max(0.0, spatial.motion_correlation)
            return round(0.70 + 0.25 * corr, 2)
        elif self.current_state in (InteractionState.RELEASING, InteractionState.RELEASED):
            return 0.80
        return 0.50

    def _build_event(self, spatial: SpatialRelationship, confidence: float) -> InteractionEvent:
        """Construct the standardized InteractionEvent."""
        return InteractionEvent(
            target_object_id=self.target_object_id,
            target_track_id=self.target_track_id,
            hand_type=spatial.hand_type,
            state=self.current_state,
            distance=spatial.normalized_distance,
            confidence=confidence,
            timestamp=self.last_update_time,
            relative_velocity=spatial.relative_velocity,
            duration_seconds=round(self.duration_in_state, 3),
            spatial=spatial,
            actor="ASTRONAUT",
            is_uncertain=self.is_uncertain,
            evidence_details={
                "overlap_iou": round(spatial.overlap_iou, 3),
                "approach_speed": spatial.approach_speed,
                "motion_correlation": spatial.motion_correlation,
                "lost_frames": self.lost_frames_count,
            },
        )

"""Multi-signal decision rules for physical hand-object interactions.

Distinguishes proximity (HAND_NEAR_OBJECT) from actual physical contact,
and verifies coupled motion before declaring grasp/move.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from core.common.config import InteractionSettings
from core.interaction.types import SpatialRelationship


@dataclass
class InteractionRuleResult:
    """Evaluation result for an interaction rule."""
    is_triggered: bool
    confidence: float
    reason: str


class InteractionRules:
    """Evaluates multi-signal criteria to classify spatial-kinematic states."""

    def __init__(self, settings: Optional[InteractionSettings] = None):
        self.cfg = settings or InteractionSettings()

    def evaluate_approach(
        self,
        spatial: SpatialRelationship,
        approach_history: list[float],
    ) -> InteractionRuleResult:
        """Determine whether the hand is purposefully approaching the target object."""
        # Must be within outer approach radius
        if spatial.normalized_distance > self.cfg.approach_distance_threshold:
            return InteractionRuleResult(False, 0.0, "Distance exceeds approach threshold")

        # Must have negative approach speed (closing distance)
        if spatial.approach_speed > self.cfg.approach_speed_threshold:
            return InteractionRuleResult(False, 0.0, "Approach speed not sufficiently negative")

        # Verify multi-frame monotonic decrease over recent history (at least 3 samples)
        if len(approach_history) >= 3:
            decreases = sum(1 for i in range(len(approach_history) - 1) if approach_history[i] >= approach_history[i + 1])
            consistency = decreases / (len(approach_history) - 1)
            if consistency >= 0.65:
                conf = min(0.95, round(0.5 + 0.5 * consistency, 2))
                return InteractionRuleResult(True, conf, f"Consistent approach over {len(approach_history)} frames")

        # Single frame approach velocity evidence
        return InteractionRuleResult(True, 0.60, "Instantaneous approach velocity verified")

    def evaluate_near(self, spatial: SpatialRelationship) -> InteractionRuleResult:
        """Determine whether hand is strictly NEAR the object without contact."""
        if (
            spatial.normalized_distance <= self.cfg.near_distance_threshold
            and spatial.normalized_distance > self.cfg.contact_distance_threshold
            and spatial.overlap_iou < self.cfg.contact_iou_threshold
        ):
            conf = min(0.90, round(1.0 - (spatial.normalized_distance / self.cfg.near_distance_threshold), 2))
            return InteractionRuleResult(True, max(0.5, conf), "Hand proximate to object boundary without contact")
        return InteractionRuleResult(False, 0.0, "Outside near proximity window")

    def evaluate_contact(
        self,
        spatial: SpatialRelationship,
        consecutive_contact_frames: int,
    ) -> InteractionRuleResult:
        """Determine whether physical contact is established using distance, IoU, and persistence."""
        has_spatial_contact = (
            spatial.normalized_distance <= self.cfg.contact_distance_threshold
            or spatial.overlap_iou >= self.cfg.contact_iou_threshold
            or spatial.relative_quadrant == "INSIDE"
        )

        if not has_spatial_contact:
            return InteractionRuleResult(False, 0.0, "No spatial overlap or contact proximity")

        if consecutive_contact_frames >= self.cfg.contact_confirmation_frames:
            # High confidence with confirmed temporal persistence
            conf = min(0.95, 0.70 + (0.05 * min(5, consecutive_contact_frames)))
            return InteractionRuleResult(True, round(conf, 2), f"Contact confirmed across {consecutive_contact_frames} frames")
        else:
            # Contact detected but awaiting persistence confirmation
            conf = 0.55
            return InteractionRuleResult(True, conf, f"Initial contact frame ({consecutive_contact_frames}/{self.cfg.contact_confirmation_frames})")

    def evaluate_coupled_motion(
        self,
        spatial: SpatialRelationship,
    ) -> InteractionRuleResult:
        """Determine whether hand and object are moving together (coupled trajectory)."""
        hand_speed = math.hypot(spatial.hand_velocity[0], spatial.hand_velocity[1])
        obj_speed = math.hypot(spatial.object_velocity[0], spatial.object_velocity[1])

        # Both entities must be moving faster than minimal speed threshold
        if hand_speed < self.cfg.coupled_motion_speed_min or obj_speed < self.cfg.coupled_motion_speed_min:
            return InteractionRuleResult(False, 0.0, "Speeds below movement threshold")

        # Cosine correlation must be high
        if spatial.motion_correlation >= self.cfg.coupled_motion_correlation_min:
            conf = min(0.98, round(spatial.motion_correlation, 2))
            return InteractionRuleResult(True, conf, f"Coupled motion verified (cosine: {spatial.motion_correlation})")

        return InteractionRuleResult(False, 0.0, f"Uncoupled motion vectors (cosine: {spatial.motion_correlation})")

    def evaluate_object_moved_alone(
        self,
        spatial: SpatialRelationship,
    ) -> InteractionRuleResult:
        """Detect negative condition: object moving independently without hand contact (Test B)."""
        obj_speed = math.hypot(spatial.object_velocity[0], spatial.object_velocity[1])
        if (
            obj_speed >= self.cfg.coupled_motion_speed_min
            and spatial.normalized_distance > self.cfg.contact_distance_threshold
            and spatial.overlap_iou < self.cfg.contact_iou_threshold
        ):
            return InteractionRuleResult(True, 0.90, "Object moving independently without hand contact")
        return InteractionRuleResult(False, 0.0, "Object stationary or in contact with hand")

    def evaluate_release(
        self,
        spatial: SpatialRelationship,
        prior_state_was_holding_or_moving: bool,
    ) -> InteractionRuleResult:
        """Determine whether hand has released the object."""
        if not prior_state_was_holding_or_moving:
            return InteractionRuleResult(False, 0.0, "Cannot release from non-holding/moving state")

        # Distance is growing and contact is broken
        contact_broken = (
            spatial.normalized_distance > self.cfg.contact_distance_threshold
            and spatial.overlap_iou < self.cfg.contact_iou_threshold
        )
        distance_growing = spatial.approach_speed > self.cfg.release_distance_growth_threshold

        if contact_broken and distance_growing:
            conf = min(0.95, round(0.70 + min(0.25, spatial.approach_speed * 2.0), 2))
            return InteractionRuleResult(True, conf, "Hand departing after holding/moving")

        if contact_broken and spatial.motion_correlation < 0.30:
            return InteractionRuleResult(True, 0.80, "Decoupled trajectory with broken contact")

        return InteractionRuleResult(False, 0.0, "Contact or coupling still present")

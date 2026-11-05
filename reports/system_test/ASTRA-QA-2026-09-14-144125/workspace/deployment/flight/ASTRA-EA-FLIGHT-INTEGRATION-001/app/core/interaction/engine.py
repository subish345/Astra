"""Spatial interaction engine computing physical relationships between hands and tracked objects.

Manages per-pair state machines, spatial kinematics, and interaction event emission.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from core.common.config import InteractionSettings
from core.common.logging import get_logger
from core.interaction.geometry import (
    calculate_box_overlap_iou,
    calculate_normalized_distance,
    calculate_pixel_distance,
    compute_approach_speed,
    compute_motion_correlation,
    compute_velocity_vector,
    determine_relative_position,
)
from core.interaction.interface import InteractionEngine
from core.interaction.state_machine import HandObjectStateMachine
from core.interaction.types import InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import HandObservation, Track, TrackState

logger = get_logger("INTERACTION")


class SpatialInteractionEngine(InteractionEngine):
    """Production implementation of InteractionEngine evaluating spatial kinematics."""

    def __init__(
        self,
        settings: Optional[InteractionSettings] = None,
        frame_width: float = 640.0,
        frame_height: float = 480.0,
    ):
        self.cfg = settings or InteractionSettings()
        self.frame_width = frame_width
        self.frame_height = frame_height

        # Key: (hand_type_str, track_id) -> HandObjectStateMachine
        self._state_machines: Dict[Tuple[str, int], HandObjectStateMachine] = {}

        # Cache previous observations for velocity and approach speed derivation
        # Key: (hand_type_str, track_id) -> (prev_timestamp, prev_hand_pos, prev_dist)
        self._prev_observations: Dict[Tuple[str, int], Tuple[float, Tuple[float, float], float]] = {}

    def process(
        self,
        tracks: List[Track],
        hands: List[HandObservation],
        timestamp: float,
    ) -> List[InteractionEvent]:
        """Compute spatial-temporal coupling between hands and tracked objects."""
        active_events: List[InteractionEvent] = []
        observed_keys: set[Tuple[str, int]] = set()

        # Filter tracks: ignore astronaut self-detections if tracked as objects
        object_tracks = [t for t in tracks if t.class_name.upper() != "ASTRONAUT"]

        for hand in hands:
            hand_type_str = hand.hand_type.value if hasattr(hand.hand_type, "value") else str(hand.hand_type)
            hand_center = hand.wrist  # Wrist or centroid

            for track in object_tracks:
                pair_key = (hand_type_str, track.track_id)
                observed_keys.add(pair_key)

                # 1. Retrieve or create state machine for this pair
                if pair_key not in self._state_machines:
                    self._state_machines[pair_key] = HandObjectStateMachine(
                        hand_type=hand_type_str,
                        target_track_id=track.track_id,
                        target_object_id=track.class_name,
                        settings=self.cfg,
                    )
                sm = self._state_machines[pair_key]

                # 2. Compute spatial metrics
                obj_center = track.center
                pix_dist = calculate_pixel_distance(hand_center, obj_center)
                norm_dist = calculate_normalized_distance(
                    hand_center,
                    obj_center,
                    frame_width=self.frame_width,
                    frame_height=self.frame_height,
                )
                overlap_iou = calculate_box_overlap_iou(hand.bbox, track.bbox)
                rel_pos = determine_relative_position(hand_center, track.bbox)

                # 3. Derive velocities and approach rate from history
                dt = 0.033  # Default nominal ~30 FPS dt
                approach_speed = 0.0
                hand_velocity = (0.0, 0.0)

                if pair_key in self._prev_observations:
                    prev_ts, prev_hand_pt, prev_norm_dist = self._prev_observations[pair_key]
                    dt = max(0.001, timestamp - prev_ts)
                    approach_speed = compute_approach_speed(norm_dist, prev_norm_dist, dt)
                    hand_velocity = compute_velocity_vector(hand_center, prev_hand_pt, dt)

                self._prev_observations[pair_key] = (timestamp, hand_center, norm_dist)

                obj_velocity = track.velocity
                rel_velocity = (
                    round(hand_velocity[0] - obj_velocity[0], 2),
                    round(hand_velocity[1] - obj_velocity[1], 2),
                )
                motion_corr = compute_motion_correlation(hand_velocity, obj_velocity)

                # 4. Construct SpatialRelationship
                spatial = SpatialRelationship(
                    hand_type=hand.hand_type,
                    target_track_id=track.track_id,
                    target_object_id=track.class_name,
                    pixel_distance=round(pix_dist, 2),
                    normalized_distance=round(norm_dist, 4),
                    overlap_iou=round(overlap_iou, 3),
                    relative_quadrant=rel_pos,
                    hand_center=hand_center,
                    object_center=obj_center,
                    hand_velocity=hand_velocity,
                    object_velocity=obj_velocity,
                    relative_velocity=rel_velocity,
                    approach_speed=approach_speed,
                    motion_correlation=motion_corr,
                )

                # 5. Advance state machine and emit event
                event = sm.update(spatial, track.state, timestamp)
                active_events.append(event)

        # 6. Handle tracks not paired with any visible hand this frame
        current_track_ids = {t.track_id for t in object_tracks}
        dead_keys = [
            k for k in self._state_machines.keys()
            if k not in observed_keys and k[1] not in current_track_ids
        ]
        for k in dead_keys:
            sm = self._state_machines[k]
            # Notify state machine that track is lost
            dummy_spatial = SpatialRelationship(
                hand_type=sm.hand_type,  # type: ignore
                target_track_id=sm.target_track_id,
                target_object_id=sm.target_object_id,
                pixel_distance=999.0,
                normalized_distance=1.0,
                overlap_iou=0.0,
                relative_quadrant="UNKNOWN",
                hand_center=(0.0, 0.0),
                object_center=(0.0, 0.0),
            )
            sm.update(dummy_spatial, TrackState.LOST, timestamp)
            del self._state_machines[k]
            self._prev_observations.pop(k, None)

        return active_events

    def reset(self) -> None:
        """Reset internal tracking and proximity history."""
        self._state_machines.clear()
        self._prev_observations.clear()
        logger.info("SpatialInteractionEngine state reset.")

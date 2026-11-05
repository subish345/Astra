"""Deterministic synthetic interaction scenarios for testing and verification.

Generates reproducible frame-by-frame PerceptionState sequences modeling positive
interactions, false positives, occlusions, and edge cases.
"""

from __future__ import annotations

from typing import List, Tuple
from core.perception.types import (
    BoundingBox,
    Detection,
    HandObservation,
    HandType,
    Keypoint,
    PerceptionState,
    Track,
    TrackState,
)


def create_mock_perception_frame(
    frame_id: int,
    timestamp: float,
    hand_pos: Tuple[float, float],
    obj_pos: Tuple[float, float],
    obj_size: Tuple[float, float] = (60.0, 60.0),
    obj_name: str = "RED_BOX",
    track_id: int = 1,
    track_state: TrackState = TrackState.VISIBLE,
    hand_type: HandType = HandType.RIGHT,
    hand_confidence: float = 0.90,
    obj_velocity: Tuple[float, float] = (0.0, 0.0),
) -> PerceptionState:
    """Helper to synthesize a single perception frame with one hand and one object track."""
    hx, hy = hand_pos
    ox, oy = obj_pos
    ow, oh = obj_size

    obj_bbox = BoundingBox(
        x1=ox - ow / 2,
        y1=oy - oh / 2,
        x2=ox + ow / 2,
        y2=oy + oh / 2,
    )

    hand_bbox = BoundingBox(
        x1=hx - 25,
        y1=hy - 25,
        x2=hx + 25,
        y2=hy + 25,
    )

    hand_kp = [
        Keypoint(x=hx, y=hy, confidence=hand_confidence, name="wrist"),
        Keypoint(x=hx + 10, y=hy - 15, confidence=hand_confidence, name="index_tip"),
    ]

    hand_obs = HandObservation(
        hand_type=hand_type,
        keypoints=hand_kp,
        confidence=hand_confidence,
        wrist=(hx, hy),
        bbox=hand_bbox,
        source="SYNTHETIC",
    )

    obj_det = Detection(
        class_name=obj_name,
        confidence=0.92,
        bbox=obj_bbox,
        track_id=track_id,
        timestamp=timestamp,
        frame_id=frame_id,
        source="SYNTHETIC",
    )

    track = Track(
        track_id=track_id,
        class_name=obj_name,
        bbox=obj_bbox,
        confidence=0.92,
        velocity=obj_velocity,
        state=track_state,
        age_frames=frame_id,
        is_active=(track_state != TrackState.LOST),
    )

    return PerceptionState(
        timestamp=timestamp,
        frame_id=frame_id,
        source_id="synthetic_sim",
        objects=[obj_det],
        hands=[hand_obs],
        tracks=[track],
        fps=30.0,
    )


def scenario_correct_grasp(num_frames: int = 25) -> List[PerceptionState]:
    """Positive Scenario: Hand approaches RED_BOX, makes contact, grasps, and lifts."""
    frames: List[PerceptionState] = []
    obj_pos = (320.0, 300.0)

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        if i < 8:
            # Phase 1: Approach (hand moves from x=150, y=150 towards obj at 320, 300)
            alpha = i / 8.0
            hx = 150.0 + alpha * (320.0 - 150.0)
            hy = 150.0 + alpha * (300.0 - 150.0)
            curr_obj_pos = obj_pos
            v_obj = (0.0, 0.0)
        elif i < 15:
            # Phase 2: Contact & Grasp (hand at object center)
            hx, hy = obj_pos
            curr_obj_pos = obj_pos
            v_obj = (0.0, 0.0)
        else:
            # Phase 3: Lift (both move upward together: dy negative)
            lift_alpha = (i - 15) / float(num_frames - 15)
            dy = -80.0 * lift_alpha
            hx = obj_pos[0]
            hy = obj_pos[1] + dy
            curr_obj_pos = (obj_pos[0], obj_pos[1] + dy)
            v_obj = (0.0, -40.0)

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=(hx, hy),
                obj_pos=curr_obj_pos,
                obj_velocity=v_obj,
            )
        )
    return frames


def scenario_false_near_object(num_frames: int = 15) -> List[PerceptionState]:
    """Negative Test A: Hand approaches near object, hovers outside contact distance, then departs."""
    frames: List[PerceptionState] = []
    obj_pos = (320.0, 300.0)

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        if i < 7:
            # Approaches to distance 120 pixels (near zone, but > contact 40 pixels)
            alpha = i / 7.0
            hx = 100.0 + alpha * 100.0  # ends at 200.0 (dist to 320 is 120px)
            hy = 300.0
        else:
            # Departs back
            beta = (i - 7) / float(num_frames - 7)
            hx = 200.0 - beta * 100.0
            hy = 300.0

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=(hx, hy),
                obj_pos=obj_pos,
            )
        )
    return frames


def scenario_object_moves_alone(num_frames: int = 15) -> List[PerceptionState]:
    """Negative Test B: Object translates across screen without hand contact (hand stationary far away)."""
    frames: List[PerceptionState] = []
    hand_pos = (100.0, 100.0)  # Far top-left

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        ox = 250.0 + (i * 12.0)  # Translating rightward
        oy = 300.0
        v_obj = (60.0, 0.0)

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=hand_pos,
                obj_pos=(ox, oy),
                obj_velocity=v_obj,
            )
        )
    return frames


def scenario_contact_no_move(num_frames: int = 20) -> List[PerceptionState]:
    """Negative Test C: Hand touches object continuously, but object never translates or lifts."""
    frames: List[PerceptionState] = []
    obj_pos = (320.0, 300.0)

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        hx = 320.0 if i >= 4 else (200.0 + i * 30.0)
        hy = 300.0

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=(hx, hy),
                obj_pos=obj_pos,
                obj_velocity=(0.0, 0.0),
            )
        )
    return frames


def scenario_occlusion(num_frames: int = 20) -> List[PerceptionState]:
    """Negative Test D: Hand and object in contact, but object is temporarily occluded for 5 frames."""
    frames: List[PerceptionState] = []
    obj_pos = (320.0, 300.0)

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        is_occluded = (8 <= i <= 12)
        state = TrackState.TEMPORARILY_LOST if is_occluded else TrackState.VISIBLE

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=obj_pos,
                obj_pos=obj_pos,
                track_state=state,
            )
        )
    return frames


def scenario_release(num_frames: int = 20) -> List[PerceptionState]:
    """Scenario: Hand holds object, then separates and moves away, leaving object at new position."""
    frames: List[PerceptionState] = []
    placed_pos = (450.0, 300.0)

    for i in range(num_frames):
        ts = round(i * 0.033, 3)
        if i < 8:
            # Holding at placed position
            hx, hy = placed_pos
        else:
            # Releasing and moving away
            delta = (i - 8) * 15.0
            hx = placed_pos[0] + delta
            hy = placed_pos[1] - delta

        frames.append(
            create_mock_perception_frame(
                frame_id=i + 1,
                timestamp=ts,
                hand_pos=(hx, hy),
                obj_pos=placed_pos,
            )
        )
    return frames

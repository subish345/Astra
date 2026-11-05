"""Unit tests for TemporalBuffer rolling window and TemporalFeatureExtractor."""

import pytest
from core.activity.temporal import TemporalBuffer, TemporalFeatureExtractor
from core.interaction.types import InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import HandType


def test_temporal_buffer_rolling_and_expiration():
    buf = TemporalBuffer(window_seconds=1.0)

    # Append at t=0.0
    ev1 = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.APPROACHING,
        distance=0.30,
        confidence=0.80,
        timestamp=0.0,
    )
    buf.append(0.0, [ev1], {1: (100.0, 100.0)})

    # Append at t=0.5
    ev2 = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.NEAR,
        distance=0.15,
        confidence=0.85,
        timestamp=0.5,
    )
    buf.append(0.5, [ev2], {1: (110.0, 100.0)})

    # Append at t=1.2 (exceeds 1.0s window from t=0.0)
    ev3 = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.CONTACT,
        distance=0.04,
        confidence=0.90,
        timestamp=1.2,
    )
    buf.append(1.2, [ev3], {1: (120.0, 100.0)})

    # ev1 at t=0.0 should have expired (cutoff = 1.2 - 1.0 = 0.2)
    history = buf.get_interaction_history("RIGHT", 1)
    timestamps = [e.timestamp for e in history]
    assert 0.0 not in timestamps
    assert 0.5 in timestamps
    assert 1.2 in timestamps

    # Check track trajectory
    traj = buf.get_track_trajectory(1)
    assert len(traj) == 2
    assert traj[0][1] == (110.0, 100.0)
    assert traj[1][1] == (120.0, 100.0)


def test_temporal_feature_extraction():
    # Trajectory over 1.0s: (100, 200) -> (150, 100) (dx=50, dy=-100)
    trajectory = [
        (0.0, (100.0, 200.0)),
        (0.5, (125.0, 150.0)),
        (1.0, (150.0, 100.0)),
    ]

    events = [
        InteractionEvent(
            target_object_id="RED_BOX",
            target_track_id=1,
            hand_type=HandType.RIGHT,
            state=InteractionState.CONTACT,
            distance=0.05,
            confidence=0.85,
            timestamp=0.0,
            spatial=SpatialRelationship(
                hand_type=HandType.RIGHT,
                target_track_id=1,
                target_object_id="RED_BOX",
                pixel_distance=20.0,
                normalized_distance=0.05,
                overlap_iou=0.2,
                relative_quadrant="INSIDE",
                hand_center=(100.0, 200.0),
                object_center=(100.0, 200.0),
                motion_correlation=0.95,
            ),
        ),
        InteractionEvent(
            target_object_id="RED_BOX",
            target_track_id=1,
            hand_type=HandType.RIGHT,
            state=InteractionState.MOVING,
            distance=0.04,
            confidence=0.90,
            timestamp=1.0,
            spatial=SpatialRelationship(
                hand_type=HandType.RIGHT,
                target_track_id=1,
                target_object_id="RED_BOX",
                pixel_distance=15.0,
                normalized_distance=0.04,
                overlap_iou=0.25,
                relative_quadrant="INSIDE",
                hand_center=(150.0, 100.0),
                object_center=(150.0, 100.0),
                motion_correlation=0.98,
            ),
        ),
    ]

    features = TemporalFeatureExtractor.extract_features(events, trajectory)

    assert features.position_delta == (50.0, -100.0)
    assert features.vertical_displacement == -100.0
    assert features.velocity == (50.0, -100.0)
    assert features.object_displacement == pytest.approx(111.8, rel=1e-2)
    assert features.hand_object_relative_motion >= 0.90
    assert features.contact_duration >= 0.03

"""Unit tests for multi-signal interaction decision rules."""

import pytest
from core.common.config import InteractionSettings
from core.interaction.rules import InteractionRules
from core.interaction.types import SpatialRelationship
from core.perception.types import HandType


@pytest.fixture
def rules():
    cfg = InteractionSettings(
        approach_distance_threshold=0.35,
        near_distance_threshold=0.18,
        contact_distance_threshold=0.08,
        contact_iou_threshold=0.05,
        approach_speed_threshold=-0.03,
        contact_confirmation_frames=3,
        coupled_motion_correlation_min=0.70,
        coupled_motion_speed_min=10.0,
    )
    return InteractionRules(cfg)


def test_approach_evaluation(rules):
    # Valid approach: within threshold, closing speed, decreasing history
    spatial = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=150.0,
        normalized_distance=0.25,
        overlap_iou=0.0,
        relative_quadrant="LEFT",
        hand_center=(100.0, 100.0),
        object_center=(250.0, 100.0),
        approach_speed=-0.08,
    )
    res = rules.evaluate_approach(spatial, approach_history=[0.35, 0.30, 0.25])
    assert res.is_triggered is True
    assert res.confidence >= 0.70

    # Invalid approach: distance too large
    spatial_far = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=400.0,
        normalized_distance=0.60,
        overlap_iou=0.0,
        relative_quadrant="LEFT",
        hand_center=(50.0, 100.0),
        object_center=(450.0, 100.0),
        approach_speed=-0.10,
    )
    assert rules.evaluate_approach(spatial_far, []).is_triggered is False


def test_near_evaluation(rules):
    # Inside near zone (between 0.08 and 0.18)
    spatial_near = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=80.0,
        normalized_distance=0.12,
        overlap_iou=0.0,
        relative_quadrant="LEFT",
        hand_center=(150.0, 100.0),
        object_center=(230.0, 100.0),
    )
    res = rules.evaluate_near(spatial_near)
    assert res.is_triggered is True

    # Inside contact zone (< 0.08) -> evaluate_near should return False
    spatial_contact = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=20.0,
        normalized_distance=0.04,
        overlap_iou=0.15,
        relative_quadrant="INSIDE",
        hand_center=(220.0, 100.0),
        object_center=(230.0, 100.0),
    )
    assert rules.evaluate_near(spatial_contact).is_triggered is False


def test_contact_evaluation_persistence(rules):
    spatial = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=20.0,
        normalized_distance=0.04,
        overlap_iou=0.20,
        relative_quadrant="INSIDE",
        hand_center=(200.0, 200.0),
        object_center=(200.0, 200.0),
    )
    # 1 frame: triggered but confidence moderate
    res1 = rules.evaluate_contact(spatial, consecutive_contact_frames=1)
    assert res1.is_triggered is True
    assert res1.confidence < 0.70

    # 3 frames (threshold met): high confidence
    res3 = rules.evaluate_contact(spatial, consecutive_contact_frames=3)
    assert res3.is_triggered is True
    assert res3.confidence >= 0.75


def test_coupled_motion_evaluation(rules):
    # Coupled motion: high speed, correlation = 0.95
    spatial_coupled = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=10.0,
        normalized_distance=0.02,
        overlap_iou=0.40,
        relative_quadrant="INSIDE",
        hand_center=(200.0, 200.0),
        object_center=(200.0, 200.0),
        hand_velocity=(30.0, -40.0),
        object_velocity=(32.0, -38.0),
        motion_correlation=0.98,
    )
    res = rules.evaluate_coupled_motion(spatial_coupled)
    assert res.is_triggered is True
    assert res.confidence >= 0.90

    # Uncoupled: orthogonal motions
    spatial_uncoupled = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=10.0,
        normalized_distance=0.02,
        overlap_iou=0.40,
        relative_quadrant="INSIDE",
        hand_center=(200.0, 200.0),
        object_center=(200.0, 200.0),
        hand_velocity=(30.0, 0.0),
        object_velocity=(0.0, 30.0),
        motion_correlation=0.0,
    )
    assert rules.evaluate_coupled_motion(spatial_uncoupled).is_triggered is False


def test_object_moved_alone_negative_condition(rules):
    # Negative Test B: object translates without hand contact
    spatial = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=250.0,
        normalized_distance=0.45,
        overlap_iou=0.0,
        relative_quadrant="LEFT",
        hand_center=(50.0, 50.0),
        object_center=(300.0, 200.0),
        object_velocity=(40.0, 0.0),
    )
    res = rules.evaluate_object_moved_alone(spatial)
    assert res.is_triggered is True
    assert res.confidence >= 0.85

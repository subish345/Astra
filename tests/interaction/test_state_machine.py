"""Unit tests for HandObjectStateMachine lifecycle and hysteresis."""

import pytest
from core.common.config import InteractionSettings
from core.interaction.state_machine import HandObjectStateMachine
from core.interaction.types import InteractionState, SpatialRelationship
from core.perception.types import HandType, TrackState


@pytest.fixture
def state_machine():
    cfg = InteractionSettings(
        approach_distance_threshold=0.35,
        near_distance_threshold=0.18,
        contact_distance_threshold=0.08,
        contact_iou_threshold=0.05,
        contact_confirmation_frames=3,
        coupled_motion_correlation_min=0.70,
        coupled_motion_speed_min=10.0,
    )
    return HandObjectStateMachine(
        hand_type="RIGHT",
        target_track_id=1,
        target_object_id="RED_BOX",
        settings=cfg,
    )


def test_state_machine_approach_to_contact_progression(state_machine):
    # Step 1: NONE -> APPROACHING
    spatial_appr = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=200.0,
        normalized_distance=0.30,
        overlap_iou=0.0,
        relative_quadrant="LEFT",
        hand_center=(120.0, 200.0),
        object_center=(320.0, 200.0),
        approach_speed=-0.08,
    )
    # Frame 1
    state_machine.update(spatial_appr, TrackState.VISIBLE, timestamp=1.0)
    # Frame 2 confirms approach
    event = state_machine.update(spatial_appr, TrackState.VISIBLE, timestamp=1.033)
    assert event.state == InteractionState.APPROACHING

    # Step 2: Contact establishes over 3 confirmation frames
    spatial_contact = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=15.0,
        normalized_distance=0.03,
        overlap_iou=0.25,
        relative_quadrant="INSIDE",
        hand_center=(310.0, 200.0),
        object_center=(320.0, 200.0),
    )
    state_machine.update(spatial_contact, TrackState.VISIBLE, timestamp=1.066)
    state_machine.update(spatial_contact, TrackState.VISIBLE, timestamp=1.100)
    event_c = state_machine.update(spatial_contact, TrackState.VISIBLE, timestamp=1.133)
    assert event_c.state == InteractionState.CONTACT
    assert event_c.confidence >= 0.70


def test_state_machine_track_loss_handling(state_machine):
    # Establish contact first
    spatial = SpatialRelationship(
        hand_type=HandType.RIGHT,
        target_track_id=1,
        target_object_id="RED_BOX",
        pixel_distance=10.0,
        normalized_distance=0.02,
        overlap_iou=0.30,
        relative_quadrant="INSIDE",
        hand_center=(320.0, 200.0),
        object_center=(320.0, 200.0),
    )
    for i in range(3):
        state_machine.update(spatial, TrackState.VISIBLE, timestamp=1.0 + i * 0.033)
    assert state_machine.current_state == InteractionState.CONTACT

    # Target track becomes temporarily lost -> event marked uncertain
    event_loss = state_machine.update(spatial, TrackState.TEMPORARILY_LOST, timestamp=1.2)
    assert event_loss.is_uncertain is True
    assert event_loss.state == InteractionState.CONTACT

    # Reacquired -> uncertainty cleared
    event_reacquired = state_machine.update(spatial, TrackState.VISIBLE, timestamp=1.233)
    assert event_reacquired.is_uncertain is False

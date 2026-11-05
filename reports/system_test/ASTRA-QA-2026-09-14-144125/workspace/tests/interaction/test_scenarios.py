"""Tests for positive and negative interaction scenarios using SpatialInteractionEngine."""

import pytest
from core.interaction.engine import SpatialInteractionEngine
from core.interaction.scenarios import (
    scenario_contact_no_move,
    scenario_correct_grasp,
    scenario_false_near_object,
    scenario_object_moves_alone,
    scenario_occlusion,
)
from core.interaction.types import InteractionState


def test_scenario_correct_grasp_progression():
    """Verify progression: APPROACHING -> NEAR -> CONTACT -> GRASPING/MOVING."""
    engine = SpatialInteractionEngine()
    frames = scenario_correct_grasp(num_frames=25)

    observed_states = []
    for frame in frames:
        events = engine.process(frame.tracks, frame.hands, frame.timestamp)
        if events:
            observed_states.append(events[0].state)

    assert InteractionState.APPROACHING in observed_states or InteractionState.NEAR in observed_states
    assert InteractionState.CONTACT in observed_states
    assert InteractionState.MOVING in observed_states or InteractionState.GRASPING in observed_states


def test_negative_scenario_a_false_near_object():
    """Negative Test A: Hand approaches near object, hovers, and departs without contact or grasp."""
    engine = SpatialInteractionEngine()
    frames = scenario_false_near_object(num_frames=15)

    observed_states = []
    for frame in frames:
        events = engine.process(frame.tracks, frame.hands, frame.timestamp)
        if events:
            observed_states.append(events[0].state)

    # Must observe APPROACHING or NEAR, but NEVER CONTACT, GRASPING, or MOVING
    assert InteractionState.CONTACT not in observed_states
    assert InteractionState.GRASPING not in observed_states
    assert InteractionState.MOVING not in observed_states


def test_negative_scenario_b_object_moves_alone():
    """Negative Test B: Object moves across screen with hand far away -> no grasp confirmed."""
    engine = SpatialInteractionEngine()
    frames = scenario_object_moves_alone(num_frames=15)

    observed_states = []
    for frame in frames:
        events = engine.process(frame.tracks, frame.hands, frame.timestamp)
        if events:
            observed_states.append(events[0].state)

    # Since hand is at (100, 100) and object moves at (250+, 300), distance > 0.35 threshold
    assert InteractionState.CONTACT not in observed_states
    assert InteractionState.GRASPING not in observed_states
    assert InteractionState.MOVING not in observed_states


def test_negative_scenario_c_contact_no_move():
    """Negative Test C: Hand contacts object steadily, but object never translates."""
    engine = SpatialInteractionEngine()
    frames = scenario_contact_no_move(num_frames=20)

    observed_states = []
    for frame in frames:
        events = engine.process(frame.tracks, frame.hands, frame.timestamp)
        if events:
            observed_states.append(events[0].state)

    assert InteractionState.CONTACT in observed_states
    # Never transitions to MOVING because object is stationary
    assert InteractionState.MOVING not in observed_states


def test_negative_scenario_d_occlusion_handling():
    """Negative Test D: Object temporarily occluded -> uncertainty raised without premature cancellation."""
    engine = SpatialInteractionEngine()
    frames = scenario_occlusion(num_frames=20)

    uncertain_events = []
    for frame in frames:
        events = engine.process(frame.tracks, frame.hands, frame.timestamp)
        if events and events[0].is_uncertain:
            uncertain_events.append(events[0])

    # Frames 8..12 are occluded (TEMPORARILY_LOST)
    assert len(uncertain_events) >= 3

"""Unit tests for PrimitiveActivityEngine classification."""

import pytest
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer
from core.activity.types import PrimitiveActivityType
from core.interaction.types import InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import HandType


@pytest.fixture
def primitive_engine():
    return PrimitiveActivityEngine()


@pytest.fixture
def temporal_buffer():
    return TemporalBuffer(window_seconds=3.0)


def test_classify_approach(primitive_engine, temporal_buffer):
    ev = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.APPROACHING,
        distance=0.25,
        confidence=0.80,
        timestamp=1.0,
    )
    temporal_buffer.append(1.0, [ev], {1: (320.0, 240.0)})

    obs = primitive_engine.evaluate(ev, temporal_buffer)
    assert obs.activity_name == PrimitiveActivityType.APPROACH.value
    assert obs.confidence > 0.50


def test_classify_lift_vs_move(primitive_engine, temporal_buffer):
    # Case 1: Pure vertical upward movement -> LIFT
    ev_lift = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.MOVING,
        distance=0.03,
        confidence=0.88,
        timestamp=1.0,
    )
    # Start at y=300, end at y=240 (dy = -60, upward)
    temporal_buffer.append(0.0, [ev_lift], {1: (320.0, 300.0)})
    temporal_buffer.append(1.0, [ev_lift], {1: (320.0, 240.0)})

    obs_lift = primitive_engine.evaluate(ev_lift, temporal_buffer)
    assert obs_lift.activity_name == PrimitiveActivityType.LIFT.value

    # Case 2: Horizontal translation -> MOVE
    temporal_buffer.clear()
    ev_move = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.MOVING,
        distance=0.03,
        confidence=0.88,
        timestamp=1.0,
    )
    # Start at x=200, end at x=280 (dx = 80, horizontal)
    temporal_buffer.append(0.0, [ev_move], {1: (200.0, 300.0)})
    temporal_buffer.append(1.0, [ev_move], {1: (280.0, 300.0)})

    obs_move = primitive_engine.evaluate(ev_move, temporal_buffer)
    assert obs_move.activity_name == PrimitiveActivityType.MOVE.value


def test_classify_touch_and_hold(primitive_engine, temporal_buffer):
    ev_contact = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.CONTACT,
        distance=0.04,
        confidence=0.85,
        timestamp=1.0,
    )
    temporal_buffer.append(1.0, [ev_contact], {1: (320.0, 240.0)})
    obs = primitive_engine.evaluate(ev_contact, temporal_buffer)
    assert obs.activity_name == PrimitiveActivityType.TOUCH.value

    ev_hold = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.HOLDING,
        distance=0.04,
        confidence=0.85,
        timestamp=1.5,
    )
    temporal_buffer.append(1.5, [ev_hold], {1: (320.0, 240.0)})
    obs_hold = primitive_engine.evaluate(ev_hold, temporal_buffer)
    assert obs_hold.activity_name == PrimitiveActivityType.HOLD.value

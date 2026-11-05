"""Unit tests for CompositeActivityEngine temporal sequence composition."""

import pytest
from core.activity.composite import CompositeActivityEngine
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityObservation,
    ActivityStatus,
    CompositeActivityType,
    PrimitiveActivityType,
    TemporalWindow,
)


def make_primitive_obs(name: str, ts: float, track_id: int = 1) -> ActivityObservation:
    return ActivityObservation(
        activity_name=name,
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        target_track_id=track_id,
        confidence=0.88,
        window=TemporalWindow(ts, ts + 0.1, []),
        status=ActivityStatus.CONFIRMED,
        confidence_level=ActivityConfidenceLevel.HIGH,
        primitives=[name],
    )


def test_pickup_composition():
    engine = CompositeActivityEngine()

    # Feed sequence: APPROACH -> GRASP -> LIFT
    obs1 = make_primitive_obs(PrimitiveActivityType.APPROACH.value, 1.0)
    obs2 = make_primitive_obs(PrimitiveActivityType.GRASP.value, 1.3)
    obs3 = make_primitive_obs(PrimitiveActivityType.LIFT.value, 1.6)

    assert engine.update(obs1) is None
    assert engine.update(obs2) is None
    comp = engine.update(obs3)

    assert comp is not None
    assert comp.activity_name == CompositeActivityType.PICKUP.value
    assert comp.confidence >= 0.80
    assert "LIFT" in comp.primitives
    assert "GRASP" in comp.primitives


def test_move_object_composition():
    engine = CompositeActivityEngine()

    # Feed sequence: HOLD -> MOVE
    obs1 = make_primitive_obs(PrimitiveActivityType.HOLD.value, 1.0)
    obs2 = make_primitive_obs(PrimitiveActivityType.MOVE.value, 1.4)

    assert engine.update(obs1) is None
    comp = engine.update(obs2)

    assert comp is not None
    assert comp.activity_name == CompositeActivityType.MOVE_OBJECT.value


def test_place_object_composition():
    engine = CompositeActivityEngine()

    # Feed sequence: MOVE -> PLACE -> RELEASE
    obs1 = make_primitive_obs(PrimitiveActivityType.MOVE.value, 1.0)
    obs2 = make_primitive_obs(PrimitiveActivityType.PLACE.value, 1.5)
    obs3 = make_primitive_obs(PrimitiveActivityType.RELEASE.value, 1.8)

    assert engine.update(obs1) is None
    assert engine.update(obs2) is not None or engine.update(obs3) is not None

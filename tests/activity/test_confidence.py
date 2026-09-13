"""Unit tests for ActivityConfidenceEngine explainable scoring and uncertainty."""

import pytest
from core.activity.confidence import ActivityConfidenceEngine
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityStatus,
    TemporalFeatureSet,
)
from core.interaction.types import InteractionEvent, InteractionState
from core.perception.types import HandType


def test_confidence_calculation_and_tier_mapping():
    engine = ActivityConfidenceEngine()

    ev = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.MOVING,
        distance=0.03,
        confidence=0.90,
        timestamp=2.0,
    )

    features = TemporalFeatureSet(
        position_delta=(60.0, 0.0),
        velocity=(30.0, 0.0),
        contact_duration=0.8,
        object_displacement=60.0,
        hand_object_relative_motion=0.95,
        duration_seconds=2.0,
    )

    score, tier, breakdown = engine.calculate_confidence(
        ev, features, hand_confidence=0.90, object_confidence=0.95
    )

    assert 0.0 <= score <= 1.0
    assert score >= 0.80
    assert tier == ActivityConfidenceLevel.HIGH
    assert "weights" in breakdown
    assert breakdown["contact_score"] >= 0.80
    assert breakdown["motion_score"] >= 0.90


def test_uncertainty_resolution_on_track_loss():
    engine = ActivityConfidenceEngine()

    ev_uncertain = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.HOLDING,
        distance=0.05,
        confidence=0.70,
        timestamp=2.0,
        is_uncertain=True,
    )
    features = TemporalFeatureSet(duration_seconds=1.0)

    status = engine.resolve_status(ev_uncertain, features, confidence=0.75)
    assert status == ActivityStatus.UNCERTAIN


def test_in_progress_resolution_on_short_duration():
    engine = ActivityConfidenceEngine()

    ev = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.CONTACT,
        distance=0.04,
        confidence=0.80,
        timestamp=0.05,
    )
    # Duration only 0.05s, below 0.20s threshold
    features = TemporalFeatureSet(duration_seconds=0.05)

    status = engine.resolve_status(ev, features, confidence=0.75)
    assert status == ActivityStatus.IN_PROGRESS

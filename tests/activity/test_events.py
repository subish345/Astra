"""Unit tests for ActivityEventBus and ActivityEventDeduplicator."""

import pytest
from core.activity.events import (
    ActivityConfirmedEvent,
    ActivityEndedEvent,
    ActivityEventBus,
    ActivityEventDeduplicator,
    ActivityStartedEvent,
    InteractionStartedEvent,
)
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityObservation,
    ActivityStatus,
    TemporalWindow,
)
from core.interaction.types import InteractionEvent, InteractionState
from core.perception.types import HandType


def test_interaction_deduplication():
    bus = ActivityEventBus()
    received = []
    bus.subscribe(lambda ev: received.append(ev))

    dedup = ActivityEventDeduplicator(bus)

    # Frame 1: APPROACHING starts
    ev1 = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.APPROACHING,
        distance=0.30,
        confidence=0.75,
        timestamp=1.0,
    )
    dedup.process_interaction(ev1)
    assert len(received) == 1
    assert isinstance(received[0], InteractionStartedEvent)

    # Frame 2-5: Identical APPROACHING state -> should NOT spam bus
    for i in range(4):
        dedup.process_interaction(ev1)
    assert len(received) == 1  # Still 1!


def test_activity_lifecycle_deduplication():
    bus = ActivityEventBus()
    received = []
    bus.subscribe(lambda ev: received.append(ev))

    dedup = ActivityEventDeduplicator(bus)

    obs_started = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        target_track_id=1,
        confidence=0.80,
        window=TemporalWindow(1.0, 1.2, []),
        status=ActivityStatus.STARTED,
    )
    dedup.process_activity(obs_started)
    assert len(received) == 1
    assert isinstance(received[0], ActivityStartedEvent)

    # Repeat same state -> no new events
    dedup.process_activity(obs_started)
    assert len(received) == 1

    # Transition to CONFIRMED
    obs_confirmed = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        target_track_id=1,
        confidence=0.88,
        window=TemporalWindow(1.0, 1.5, []),
        status=ActivityStatus.CONFIRMED,
        confidence_level=ActivityConfidenceLevel.HIGH,
    )
    dedup.process_activity(obs_confirmed)
    assert len(received) == 2
    assert isinstance(received[1], ActivityConfirmedEvent)

"""Typed event contracts and deduplicating event bus for interactions and activities.

Ensures clean lifecycle telemetry without flooding the bus with identical per-frame events.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
from core.activity.types import ActivityObservation, ActivityStatus
from core.interaction.types import InteractionEvent, InteractionState
from core.mission.events import BaseEvent, generate_event_id, utc_now


# --- Interaction Lifecycle Events ---

class InteractionStartedEvent(BaseEvent):
    interaction_id: str
    hand_type: str
    target_object_id: str
    target_track_id: int
    initial_state: str
    timestamp_mono: float


class InteractionUpdatedEvent(BaseEvent):
    interaction_id: str
    state: str
    confidence: float
    distance: float
    duration_seconds: float
    timestamp_mono: float


class InteractionConfirmedEvent(BaseEvent):
    interaction_id: str
    state: str
    confidence: float
    duration_seconds: float
    timestamp_mono: float


class InteractionEndedEvent(BaseEvent):
    interaction_id: str
    final_state: str
    total_duration_seconds: float
    timestamp_mono: float


# --- Activity Lifecycle Events ---

class ActivityStartedEvent(BaseEvent):
    activity_id: str
    activity_name: str
    actor: str
    target_object_id: str
    confidence: float
    timestamp_mono: float


class ActivityUpdatedEvent(BaseEvent):
    activity_id: str
    activity_name: str
    confidence: float
    duration_seconds: float
    timestamp_mono: float


class ActivityConfirmedEvent(BaseEvent):
    activity_id: str
    activity_name: str
    confidence: float
    confidence_tier: str
    primitives: List[str]
    timestamp_mono: float


class ActivityUncertainEvent(BaseEvent):
    activity_id: str
    activity_name: str
    reason: str
    timestamp_mono: float


class ActivityCancelledEvent(BaseEvent):
    activity_id: str
    activity_name: str
    reason: str
    timestamp_mono: float


class ActivityEndedEvent(BaseEvent):
    activity_id: str
    activity_name: str
    total_duration_seconds: float
    timestamp_mono: float


# --- Event Bus & Deduplicator ---

class ActivityEventBus:
    """Publish-subscribe bus for interaction and activity lifecycle events."""

    def __init__(self):
        self._subscribers: List[Callable[[BaseEvent], None]] = []

    def subscribe(self, callback: Callable[[BaseEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: BaseEvent) -> None:
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception as exc:
                pass


class ActivityEventDeduplicator:
    """Stateful filter preventing repetitive event spam during sustained actions."""

    def __init__(self, event_bus: Optional[ActivityEventBus] = None):
        self.bus = event_bus or ActivityEventBus()
        # Key: (actor, track_id) -> (last_activity_name, last_status, activity_id)
        self._active_activities: Dict[Tuple[str, int], Tuple[str, ActivityStatus, str]] = {}
        # Key: (hand_type, track_id) -> (last_state, interaction_id)
        self._active_interactions: Dict[Tuple[str, int], Tuple[InteractionState, str]] = {}

    def process_interaction(self, event: InteractionEvent) -> None:
        """Evaluate interaction event and emit deduplicated lifecycle events."""
        hand_str = event.hand_type.value if hasattr(event.hand_type, "value") else str(event.hand_type)
        key = (hand_str, event.target_track_id)

        prev_info = self._active_interactions.get(key)

        if prev_info is None:
            if event.state != InteractionState.NONE:
                self._active_interactions[key] = (event.state, event.interaction_id)
                self.bus.publish(
                    InteractionStartedEvent(
                        interaction_id=event.interaction_id,
                        hand_type=hand_str,
                        target_object_id=event.target_object_id,
                        target_track_id=event.target_track_id,
                        initial_state=event.state.value,
                        timestamp_mono=event.timestamp,
                    )
                )
        else:
            prev_state, int_id = prev_info
            if event.state != prev_state:
                if event.state in (InteractionState.RELEASED, InteractionState.NONE):
                    self.bus.publish(
                        InteractionEndedEvent(
                            interaction_id=int_id,
                            final_state=event.state.value,
                            total_duration_seconds=event.duration_seconds,
                            timestamp_mono=event.timestamp,
                        )
                    )
                    self._active_interactions.pop(key, None)
                else:
                    self._active_interactions[key] = (event.state, int_id)
                    if event.state in (InteractionState.CONTACT, InteractionState.GRASPING, InteractionState.HOLDING):
                        self.bus.publish(
                            InteractionConfirmedEvent(
                                interaction_id=int_id,
                                state=event.state.value,
                                confidence=event.confidence,
                                duration_seconds=event.duration_seconds,
                                timestamp_mono=event.timestamp,
                            )
                        )

    def process_activity(self, obs: ActivityObservation) -> None:
        """Evaluate activity observation and emit deduplicated lifecycle events."""
        key = (obs.actor, obs.target_track_id or 0)
        prev = self._active_activities.get(key)

        if prev is None:
            if obs.status != ActivityStatus.ENDED:
                self._active_activities[key] = (obs.activity_name, obs.status, obs.activity_id)
                self.bus.publish(
                    ActivityStartedEvent(
                        activity_id=obs.activity_id,
                        activity_name=obs.activity_name,
                        actor=obs.actor,
                        target_object_id=obs.target_object_id,
                        confidence=obs.confidence,
                        timestamp_mono=obs.start_time,
                    )
                )
        else:
            prev_name, prev_status, act_id = prev

            # Activity or status changed
            if obs.activity_name != prev_name or obs.status != prev_status:
                if obs.status == ActivityStatus.ENDED:
                    self.bus.publish(
                        ActivityEndedEvent(
                            activity_id=act_id,
                            activity_name=prev_name,
                            total_duration_seconds=obs.duration_seconds,
                            timestamp_mono=obs.end_time,
                        )
                    )
                    self._active_activities.pop(key, None)
                elif obs.status == ActivityStatus.CONFIRMED:
                    self._active_activities[key] = (obs.activity_name, obs.status, act_id)
                    self.bus.publish(
                        ActivityConfirmedEvent(
                            activity_id=act_id,
                            activity_name=obs.activity_name,
                            confidence=obs.confidence,
                            confidence_tier=obs.confidence_level.value,
                            primitives=obs.primitives,
                            timestamp_mono=obs.end_time,
                        )
                    )
                elif obs.status == ActivityStatus.UNCERTAIN:
                    self._active_activities[key] = (obs.activity_name, obs.status, act_id)
                    self.bus.publish(
                        ActivityUncertainEvent(
                            activity_id=act_id,
                            activity_name=obs.activity_name,
                            reason="Visual occlusion or low observation confidence",
                            timestamp_mono=obs.end_time,
                        )
                    )
                elif obs.status == ActivityStatus.CANCELLED:
                    self.bus.publish(
                        ActivityCancelledEvent(
                            activity_id=act_id,
                            activity_name=prev_name,
                            reason="Action aborted prior to confirmation",
                            timestamp_mono=obs.end_time,
                        )
                    )
                    self._active_activities.pop(key, None)

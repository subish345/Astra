"""Typed perception events and lightweight event bus for ASTRA-EA.

Decouples the high-frequency perception pipeline from UI observers, logging,
and downstream reasoning engines.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Type

from core.perception.types import (
    Detection,
    HandObservation,
    PerceptionState,
    PoseObservation,
    Track,
)


@dataclass
class PerceptionEvent:
    """Base class for all perception events."""
    timestamp: float
    frame_id: int


@dataclass
class FrameCapturedEvent(PerceptionEvent):
    source_id: str
    width: int
    height: int
    fps: float


@dataclass
class ObjectDetectedEvent(PerceptionEvent):
    detection: Detection


@dataclass
class ObjectLostEvent(PerceptionEvent):
    track_id: int
    class_name: str
    last_known_bbox: Any


@dataclass
class PersonDetectedEvent(PerceptionEvent):
    person_id: int
    confidence: float


@dataclass
class PoseUpdatedEvent(PerceptionEvent):
    pose: PoseObservation


@dataclass
class HandDetectedEvent(PerceptionEvent):
    hand: HandObservation


@dataclass
class TrackCreatedEvent(PerceptionEvent):
    track: Track


@dataclass
class TrackLostEvent(PerceptionEvent):
    track: Track
    reason: str = "TIMEOUT"


@dataclass
class PerceptionUpdatedEvent(PerceptionEvent):
    state: PerceptionState


class PerceptionEventBus:
    """Thread-safe publish/subscribe bus for perception events."""

    def __init__(self):
        self._subscribers: Dict[Type[PerceptionEvent], List[Callable[[Any], None]]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_type: Type[PerceptionEvent], callback: Callable[[Any], None]) -> None:
        """Register a callback for an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def publish(self, event: PerceptionEvent) -> None:
        """Dispatch event to registered callbacks."""
        event_cls = type(event)
        with self._lock:
            callbacks = list(self._subscribers.get(event_cls, []))
            # Also dispatch to base PerceptionEvent subscribers
            if PerceptionEvent in self._subscribers and event_cls is not PerceptionEvent:
                callbacks.extend(self._subscribers[PerceptionEvent])

        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                pass

"""Unified Event Bus and Telemetry Broker for ASTRA-EA.

Provides non-blocking, thread-safe publish/subscribe messaging across Onboard Core
services, Mission Console UI bridges, and Ground Monitor streaming components.
Enforces typed correlation IDs across all mission events for causal traceability.
"""

from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type

from core.common.logging import get_logger

logger = get_logger("EVENT_BUS")


@dataclass
class CorrelationContext:
    """Correlation IDs tracing an event through the causality graph."""
    mission_id: str
    run_id: str
    experiment_id: str
    step_id: Optional[str] = None
    parent_event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "step_id": self.step_id,
            "parent_event_id": self.parent_event_id,
        }


@dataclass
class EnvelopeEvent:
    """Standardized event envelope wrapping any mission payload."""
    event_id: str
    event_type: str
    sequence_num: int
    timestamp_wall: datetime
    timestamp_mono: float
    context: CorrelationContext
    payload: Dict[str, Any]
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL

    @property
    def sequence(self) -> int:
        return self.sequence_num

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sequence_num": self.sequence_num,
            "sequence": self.sequence_num,
            "timestamp": self.timestamp_wall.isoformat(),
            "timestamp_mono": round(self.timestamp_mono, 4),
            "context": self.context.to_dict(),
            "severity": self.severity,
            "payload": self.payload,
        }


class UnifiedEventBus:
    """Centralized, asynchronous, thread-safe event bus."""

    def __init__(self, maxsize: int = 2000) -> None:
        self._lock = threading.RLock()
        self._sequence_counter: int = 0
        self._subscribers: Dict[str, List[Callable[[EnvelopeEvent], None]]] = {}
        self._global_subscribers: List[Callable[[EnvelopeEvent], None]] = []
        self._recent_events: List[EnvelopeEvent] = []
        self._max_history: int = 500

    def subscribe(self, event_type_or_handler: Any, handler: Optional[Callable[[EnvelopeEvent], None]] = None) -> None:
        """Subscribe to events of a specific type or globally if only handler provided."""
        if callable(event_type_or_handler) and handler is None:
            self.subscribe_all(event_type_or_handler)
            return

        event_type = str(event_type_or_handler)
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler and handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: Callable[[EnvelopeEvent], None]) -> None:
        """Subscribe to all events across the bus."""
        with self._lock:
            if handler not in self._global_subscribers:
                self._global_subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[EnvelopeEvent], None]) -> None:
        """Unsubscribe handler from all channels."""
        with self._lock:
            for subs in self._subscribers.values():
                if handler in subs:
                    subs.remove(handler)
            if handler in self._global_subscribers:
                self._global_subscribers.remove(handler)

    def publish(
        self,
        event_type: str,
        context: CorrelationContext,
        payload: Dict[str, Any],
        severity: str = "INFO",
        parent_event_id: Optional[str] = None,
    ) -> EnvelopeEvent:
        """Create and publish an envelope event."""
        with self._lock:
            self._sequence_counter += 1
            seq = self._sequence_counter
            now_mono = time.monotonic()
            now_wall = datetime.now(timezone.utc)
            event_id = f"EVT_{seq:06d}_{uuid.uuid4().hex[:6].upper()}"

            if parent_event_id:
                context.parent_event_id = parent_event_id

            event = EnvelopeEvent(
                event_id=event_id,
                event_type=event_type,
                sequence_num=seq,
                timestamp_wall=now_wall,
                timestamp_mono=now_mono,
                context=context,
                payload=payload,
                severity=severity,
            )

            self._recent_events.append(event)
            if len(self._recent_events) > self._max_history:
                self._recent_events.pop(0)

            # Copy subscriber lists for lock-free invocation
            target_handlers = list(self._subscribers.get(event_type, []))
            global_handlers = list(self._global_subscribers)

        # Dispatch handlers
        for handler in target_handlers + global_handlers:
            try:
                handler(event)
            except Exception as exc:
                logger.error("Error in event handler for %s: %s", event_type, exc)

        return event

    def get_recent_events(self, limit: int = 100) -> List[EnvelopeEvent]:
        """Return snapshot of most recent events."""
        with self._lock:
            return list(self._recent_events[-limit:])

    def clear(self) -> None:
        """Reset sequence counter and history."""
        with self._lock:
            self._sequence_counter = 0
            self._recent_events.clear()

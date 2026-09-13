# ==============================================================================
# ASTRA-EA Ground Telemetry Event Publisher
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Thread-safe event publisher maintaining sequence ordering and replay history."""

from __future__ import annotations

import collections
import logging
import queue
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

from streaming.events.schema import EventSeverity, EventType, GroundEvent

logger = logging.getLogger("event_publisher")


class EventPublisher:
    """Thread-safe publisher dispatching telemetry events to listeners with replay buffer."""

    def __init__(self, buffer_capacity: int = 500) -> None:
        self.buffer_capacity = buffer_capacity
        self._lock = threading.Lock()
        self._sequence_counter: int = 0
        self._history: collections.deque[GroundEvent] = collections.deque(maxlen=buffer_capacity)
        self._listeners: Set[queue.Queue[GroundEvent]] = set()

    @property
    def current_sequence(self) -> int:
        """Latest emitted sequence number."""
        with self._lock:
            return self._sequence_counter

    def register_listener(self, q: queue.Queue[GroundEvent]) -> None:
        """Register a client queue to receive live published events."""
        with self._lock:
            self._listeners.add(q)
            logger.debug("Registered event listener (Active: %d)", len(self._listeners))

    def unregister_listener(self, q: queue.Queue[GroundEvent]) -> None:
        """Unregister a client queue."""
        with self._lock:
            self._listeners.discard(q)
            logger.debug("Unregistered event listener (Active: %d)", len(self._listeners))

    def create_event(
        self,
        event_type: EventType,
        experiment_id: str = "DEMO_EXP_001",
        run_id: str = "RUN_0001",
        step_id: Optional[str] = None,
        status: str = "",
        severity: EventSeverity = EventSeverity.INFO,
        message: str = "",
        correlation_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> GroundEvent:
        """Construct a new GroundEvent with an atomic sequence number."""
        with self._lock:
            self._sequence_counter += 1
            seq = self._sequence_counter
            evt_id = f"EVT_{seq:06d}_{uuid.uuid4().hex[:6].upper()}"

            event = GroundEvent(
                event_id=evt_id,
                sequence_num=seq,
                experiment_id=experiment_id,
                run_id=run_id,
                event_type=event_type,
                step_id=step_id,
                status=status,
                severity=severity,
                message=message,
                correlation_id=correlation_id,
                evidence_id=evidence_id,
                payload=payload or {},
            )
            self._history.append(event)
            listeners_snapshot = list(self._listeners)

        # Broadcast to all registered listeners
        for q in listeners_snapshot:
            try:
                # If listener queue is full, drop oldest item to maintain real-time telemetry
                if q.full():
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
                q.put_nowait(event)
            except Exception as exc:
                logger.debug("Failed to deliver event to listener: %s", exc)

        return event

    def publish(self, event: GroundEvent) -> bool:
        """Publish an existing GroundEvent object. Assigns sequence if not set."""
        with self._lock:
            if event.sequence_num <= 0:
                self._sequence_counter += 1
                event = event.model_copy(update={"sequence_num": self._sequence_counter})
            self._history.append(event)
            listeners_snapshot = list(self._listeners)

        for q in listeners_snapshot:
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        pass
                q.put_nowait(event)
            except Exception:
                pass
        return True

    def get_events_since(self, since_sequence_num: int) -> List[GroundEvent]:
        """Return all historical events with sequence numbers strictly greater than `since_sequence_num`."""
        with self._lock:
            return [e for e in self._history if e.sequence_num > since_sequence_num]

    def get_recent_events(self, limit: int = 50) -> List[GroundEvent]:
        """Return the most recent `limit` events in chronological order."""
        with self._lock:
            events = list(self._history)
            return events[-limit:] if len(events) > limit else events

    def get_last_event(self) -> Optional[GroundEvent]:
        """Return the most recently published event."""
        with self._lock:
            return self._history[-1] if self._history else None

"""Abstract interface and test stubs for the ASTRA-EA interaction engine.

Translates object tracks and hand detections into physical interaction states.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.interaction.types import InteractionEvent
from core.perception.types import HandObservation, Track


class InteractionEngine(ABC):
    """Abstract interface for hand-object interaction estimation."""

    @abstractmethod
    def process(
        self,
        tracks: List[Track],
        hands: List[HandObservation],
        timestamp: float,
    ) -> List[InteractionEvent]:
        """Compute spatial-temporal coupling between hands and tracked objects."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracking and proximity history."""
        pass


class StubInteractionEngine(InteractionEngine):
    """Development stub returning configured interaction events for pipeline integration testing."""

    def __init__(self, predefined_events: List[InteractionEvent] = None):
        self.predefined_events = predefined_events or []

    def process(
        self,
        tracks: List[Track],
        hands: List[HandObservation],
        timestamp: float,
    ) -> List[InteractionEvent]:
        return list(self.predefined_events)

    def reset(self) -> None:
        pass

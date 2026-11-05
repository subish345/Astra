"""Abstract interface and test stubs for the ASTRA-EA activity recognition tier.

Transforms sequences of interaction events across temporal windows into discrete
experiment activities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.activity.types import ActivityObservation
from core.interaction.types import InteractionEvent


class ActivityRecognizer(ABC):
    """Abstract interface for temporal activity recognition."""

    @abstractmethod
    def update(self, interactions: List[InteractionEvent], timestamp: float) -> List[ActivityObservation]:
        """Incorporate new interaction observations and return newly recognized activities."""
        pass

    @abstractmethod
    def flush(self) -> List[ActivityObservation]:
        """Flush the active observation buffer and return any remaining completed activities."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Clear temporal buffer."""
        pass


class StubActivityRecognizer(ActivityRecognizer):
    """Development double for activity recognition pipeline integration testing."""

    def __init__(self, predefined_activities: List[ActivityObservation] = None):
        self.predefined = predefined_activities or []

    def update(self, interactions: List[InteractionEvent], timestamp: float) -> List[ActivityObservation]:
        return list(self.predefined)

    def flush(self) -> List[ActivityObservation]:
        return []

    def reset(self) -> None:
        pass

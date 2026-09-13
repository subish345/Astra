"""Abstract multi-object tracker interface for ASTRA-EA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.perception.types import Detection, Track


class Tracker(ABC):
    """Abstract interface for persistent identity tracking across temporal frames."""

    @abstractmethod
    def update(self, detections: List[Detection], frame_id: int) -> List[Track]:
        """Associate detections with existing tracks and update kinematics."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracking state and identity counters."""
        pass

    @property
    @abstractmethod
    def tracker_name(self) -> str:
        """Return tracking algorithm name."""
        pass

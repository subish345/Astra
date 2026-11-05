"""Abstract hand detector interface for ASTRA-EA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.camera.interface import FrameData
from core.perception.types import HandObservation


class HandDetector(ABC):
    """Abstract interface for hand detection and keypoint extraction."""

    @abstractmethod
    def detect(self, frame: FrameData) -> List[HandObservation]:
        """Detect hands and extract wrist/palm/finger landmarks."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier."""
        pass

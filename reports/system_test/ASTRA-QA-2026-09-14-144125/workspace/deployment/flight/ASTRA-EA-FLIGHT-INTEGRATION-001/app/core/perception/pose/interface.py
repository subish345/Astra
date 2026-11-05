"""Abstract pose estimator interface for ASTRA-EA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.camera.interface import FrameData
from core.perception.types import PoseObservation


class PoseEstimator(ABC):
    """Abstract interface for astronaut pose estimation."""

    @abstractmethod
    def estimate(self, frame: FrameData) -> List[PoseObservation]:
        """Extract skeletal joints and body posture."""
        pass

    @abstractmethod
    def get_supported_landmarks(self) -> List[str]:
        """Return list of anatomical keypoints detected by this model."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier."""
        pass

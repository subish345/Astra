"""Object detection abstract interface for ASTRA-EA.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from core.camera.interface import FrameData
from core.perception.types import Detection


class ObjectDetector(ABC):
    """Abstract interface for scientific experiment object detection."""

    @abstractmethod
    def detect(self, frame: FrameData) -> List[Detection]:
        """Extract detected entities and bounding boxes from a frame."""
        pass

    @abstractmethod
    def get_supported_classes(self) -> List[str]:
        """Return list of detectable object class names."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return name/identifier of active detector backend."""
        pass

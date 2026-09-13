"""Camera and video source interfaces for ASTRA-EA.

Decouples physical capture hardware (USB, MIPI, CSI) and recorded video files
from downstream perception and assurance pipelines.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
import numpy as np


@dataclass
class FrameData:
    """Standardized frame container passed to perception and circular buffers."""
    frame_id: int
    image: np.ndarray
    timestamp_mono: float
    timestamp_wall: datetime
    source_id: str

    @property
    def height(self) -> int:
        return self.image.shape[0]

    @property
    def width(self) -> int:
        return self.image.shape[1]

    @property
    def channels(self) -> int:
        return self.image.shape[2] if len(self.image.shape) > 2 else 1


class CameraSource(ABC):
    """Abstract interface for video ingestion sources."""

    @abstractmethod
    def start(self) -> bool:
        """Initialize and open the video stream. Returns True if successful."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Close the stream and release underlying hardware resources."""
        pass

    @abstractmethod
    def read(self) -> Optional[FrameData]:
        """Read the next video frame. Returns None if stream ended or frame unavailable."""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """Return operational status string: 'OPEN', 'CLOSED', 'ERROR', 'DEGRADED'."""
        pass

    @abstractmethod
    def get_fps(self) -> float:
        """Return observed or configured frame rate."""
        pass

    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """Return (width, height) resolution tuple."""
        pass

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Return True if camera source is actively producing frames."""
        pass

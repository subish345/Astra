# ==============================================================================
# ASTRA-EA Streaming Protocol Interfaces
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Abstract protocol interfaces for video and event streaming servers and clients."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import numpy as np


class IVideoStreamServer(ABC):
    """Interface for video stream servers."""

    @abstractmethod
    def start(self) -> None:
        """Start the video stream server in a background thread/process."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the video stream server and release all resources."""
        pass

    @abstractmethod
    def publish_frame(self, frame: np.ndarray) -> bool:
        """Non-blocking submission of a new raw frame for stream distribution.

        Returns True if frame was enqueued, False if dropped due to backpressure.
        Must NEVER block the caller.
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return True if the server is active and serving clients."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Return real-time stream diagnostics (FPS, bitrate, client count, drops)."""
        pass


class IEventStreamServer(ABC):
    """Interface for lightweight ground telemetry and event stream servers."""

    @abstractmethod
    def start(self) -> None:
        """Start the event stream server."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the event stream server."""
        pass

    @abstractmethod
    def publish_event(self, event: Any) -> bool:
        """Publish a typed event to all connected ground clients.

        Must never block or raise exceptions that could interrupt onboard autonomy.
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return True if server is listening and healthy."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Return event server metrics (connected clients, total events, dropped)."""
        pass


class IStreamClient(ABC):
    """Interface for ground clients receiving video or event streams."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to remote endpoint."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect and cleanup connection."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if link is active."""
        pass

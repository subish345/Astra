# ==============================================================================
# ASTRA-EA Video Stream Configuration
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Configuration models and quality profiles for local IP video streaming."""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple
from pydantic import BaseModel, Field


class StreamQuality(str, Enum):
    """Preset video stream quality tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Standard resolution and encoder presets: (width, height, default_fps, jpeg_quality)
QUALITY_PRESETS: Dict[StreamQuality, Tuple[int, int, int, int]] = {
    StreamQuality.LOW: (640, 360, 15, 65),
    StreamQuality.MEDIUM: (1280, 720, 15, 75),
    StreamQuality.HIGH: (1920, 1080, 20, 85),
}


class VideoStreamConfig(BaseModel):
    """Configuration model for video streaming server."""
    enabled: bool = Field(default=True, description="Enable video stream server")
    host: str = Field(default="127.0.0.1", description="Bind address (default localhost for air-gap safety)")
    port: int = Field(default=8554, ge=1024, le=65535, description="HTTP MJPEG streaming port")
    quality: StreamQuality = Field(default=StreamQuality.MEDIUM, description="Quality preset")
    width: int = Field(default=1280, gt=100, description="Stream width in pixels")
    height: int = Field(default=720, gt=100, description="Stream height in pixels")
    fps: int = Field(default=15, ge=1, le=60, description="Target streaming frame rate")
    jpeg_quality: int = Field(default=75, ge=10, le=100, description="JPEG compression quality (10-100)")
    protocol: str = Field(default="mjpeg_http", description="Streaming protocol (mjpeg_http)")
    client_timeout_seconds: float = Field(default=5.0, ge=1.0, description="Client read timeout before disconnect")
    max_clients: int = Field(default=8, ge=1, le=32, description="Maximum concurrent ground clients")
    max_queue_size: int = Field(default=1, ge=1, le=5, description="Internal frame buffer capacity (1=latest frame only)")

    def apply_quality_preset(self, quality: StreamQuality) -> None:
        """Apply parameters from a quality preset."""
        w, h, fps, jq = QUALITY_PRESETS[quality]
        self.quality = quality
        self.width = w
        self.height = h
        self.fps = fps
        self.jpeg_quality = jq

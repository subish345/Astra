# ==============================================================================
# ASTRA-EA Video Streaming Package
# ==============================================================================
"""Video streaming package supporting local IP MJPEG distribution and reception."""

from __future__ import annotations

from streaming.video.client import VideoStreamClient
from streaming.video.config import StreamQuality, VideoStreamConfig
from streaming.video.encoder import StreamEncoder
from streaming.video.server import VideoStreamServer

__all__ = [
    "VideoStreamConfig",
    "StreamQuality",
    "StreamEncoder",
    "VideoStreamServer",
    "VideoStreamClient",
]

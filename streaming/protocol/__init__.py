# ==============================================================================
# ASTRA-EA Streaming Protocols
# ==============================================================================
"""Streaming protocol interfaces and definitions."""

from __future__ import annotations

from streaming.protocol.base import IEventStreamServer, IStreamClient, IVideoStreamServer

__all__ = ["IVideoStreamServer", "IEventStreamServer", "IStreamClient"]

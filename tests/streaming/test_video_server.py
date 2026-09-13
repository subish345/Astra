# ==============================================================================
# ASTRA-EA Video Stream Server & Encoder Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Automated tests for VideoStreamServer, StreamEncoder, and VideoStreamClient."""

from __future__ import annotations

import time
import cv2
import numpy as np
import pytest

from streaming.video.client import VideoStreamClient
from streaming.video.config import StreamQuality, VideoStreamConfig
from streaming.video.encoder import StreamEncoder
from streaming.video.server import VideoStreamServer


def test_video_stream_config_presets() -> None:
    """Verify quality presets set correct dimensions and frame rates."""
    cfg = VideoStreamConfig()
    cfg.apply_quality_preset(StreamQuality.LOW)
    assert cfg.width == 640
    assert cfg.height == 360
    assert cfg.jpeg_quality == 65

    cfg.apply_quality_preset(StreamQuality.HIGH)
    assert cfg.width == 1920
    assert cfg.height == 1080
    assert cfg.jpeg_quality == 85


def test_stream_encoder() -> None:
    """Verify frame encoding, resizing, and stats."""
    cfg = VideoStreamConfig(width=320, height=240, jpeg_quality=70)
    encoder = StreamEncoder(cfg)

    # 1. Valid frame
    raw_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(raw_frame, (320, 240), 50, (0, 255, 0), -1)

    jpeg_bytes = encoder.encode(raw_frame)
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 0
    assert jpeg_bytes.startswith(b"\xff\xd8")  # JPEG SOI marker

    stats = encoder.get_stats()
    assert stats["total_encoded"] == 1.0
    assert stats["total_dropped"] == 0.0
    assert stats["last_encode_ms"] > 0.0

    # 2. None frame
    assert encoder.encode(None) is None


def test_video_stream_server_and_client_loopback() -> None:
    """Verify live HTTP multipart streaming, client reception, and clean shutdown."""
    test_port = 28560
    cfg = VideoStreamConfig(port=test_port, host="127.0.0.1", width=320, height=240, fps=15)
    server = VideoStreamServer(cfg)
    server.start()
    assert server.is_running

    received_frames = []

    def on_frame(frame: np.ndarray, metrics: dict) -> None:
        received_frames.append(frame)

    client = VideoStreamClient(
        stream_url=f"http://127.0.0.1:{test_port}/video",
        on_frame_callback=on_frame,
    )
    client.connect()
    time.sleep(0.3)

    # Publish frames
    test_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    for _ in range(10):
        server.publish_frame(test_frame)
        time.sleep(0.03)

    time.sleep(0.5)
    client.disconnect()
    server.stop()

    assert not server.is_running
    assert len(received_frames) > 0
    assert received_frames[0].shape == (240, 320, 3)

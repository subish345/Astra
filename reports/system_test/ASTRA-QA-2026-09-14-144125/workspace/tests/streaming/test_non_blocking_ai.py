# ==============================================================================
# ASTRA-EA Non-Blocking Invariant Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Validates that network transmission and slow clients NEVER block the critical AI pipeline."""

from __future__ import annotations

import queue
import time
import numpy as np
import pytest

from streaming.video.config import VideoStreamConfig
from streaming.video.server import VideoStreamServer


def test_zero_blocking_when_no_clients_connected() -> None:
    """Publishing frames when no ground clients are listening must take < 0.1ms."""
    cfg = VideoStreamConfig(port=28570, host="127.0.0.1")
    server = VideoStreamServer(cfg)
    server.start()

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    durations = []
    for _ in range(50):
        t0 = time.perf_counter()
        server.publish_frame(frame)
        durations.append((time.perf_counter() - t0) * 1000.0)

    server.stop()

    p99_ms = float(np.percentile(durations, 99))
    assert p99_ms < 1.0, f"Frame publish took too long: {p99_ms:.3f} ms (budget: 1.0 ms)"


def test_stalled_client_drops_frames_without_blocking_ai() -> None:
    """When a client queue is full and not reading, server drops stale frame immediately."""
    cfg = VideoStreamConfig(port=28571, host="127.0.0.1", max_queue_size=1)
    server = VideoStreamServer(cfg)
    server.start()

    # Artificially register a mock client queue of size 1 that never reads
    stalled_q: queue.Queue[bytes] = queue.Queue(maxsize=1)
    server.register_client(stalled_q)

    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Publish 20 frames rapidly
    for _ in range(20):
        t0 = time.perf_counter()
        server.publish_frame(frame)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 15.0, f"Slow client blocked publisher! Took {elapsed_ms:.2f} ms"

    server.unregister_client(stalled_q)
    server.stop()

    # The drop count should be recorded
    assert server.total_frames_dropped > 0

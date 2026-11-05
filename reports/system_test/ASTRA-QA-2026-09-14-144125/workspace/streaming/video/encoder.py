# ==============================================================================
# ASTRA-EA Video Stream Encoder
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Frame scaling and JPEG compression encoder for local IP video streaming."""

from __future__ import annotations

import time
from typing import Dict, Optional, Tuple
import cv2
import numpy as np

from streaming.video.config import VideoStreamConfig


class StreamEncoder:
    """Encodes raw BGR frames to JPEG format according to stream configuration."""

    def __init__(self, config: Optional[VideoStreamConfig] = None) -> None:
        self.config = config or VideoStreamConfig()
        self._encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.config.jpeg_quality)]
        
        # Performance tracking
        self.total_encoded: int = 0
        self.total_dropped: int = 0
        self.last_encode_duration_ms: float = 0.0
        self.last_frame_bytes: int = 0
        self._cumulative_encode_ms: float = 0.0

    def update_config(self, config: VideoStreamConfig) -> None:
        """Update encoding configuration at runtime."""
        self.config = config
        self._encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.config.jpeg_quality)]

    def encode(self, frame: np.ndarray) -> Optional[bytes]:
        """Resize and encode a raw frame to JPEG bytes.

        Returns JPEG byte string, or None if encoding fails.
        """
        if frame is None or frame.size == 0:
            return None

        t0 = time.perf_counter()
        try:
            h, w = frame.shape[:2]
            target_w, target_h = self.config.width, self.config.height

            # Resize only if target dimensions differ
            if (w, h) != (target_w, target_h):
                proc_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
            else:
                proc_frame = frame

            success, encoded_buf = cv2.imencode(".jpg", proc_frame, self._encode_params)
            if not success:
                self.total_dropped += 1
                return None

            jpeg_bytes = encoded_buf.tobytes()
            duration_ms = (time.perf_counter() - t0) * 1000.0

            self.total_encoded += 1
            self.last_encode_duration_ms = duration_ms
            self.last_frame_bytes = len(jpeg_bytes)
            self._cumulative_encode_ms += duration_ms

            return jpeg_bytes

        except Exception:
            self.total_dropped += 1
            return None

    def get_stats(self) -> Dict[str, float]:
        """Return empirical encoder metrics."""
        avg_ms = (
            (self._cumulative_encode_ms / self.total_encoded)
            if self.total_encoded > 0
            else 0.0
        )
        return {
            "total_encoded": float(self.total_encoded),
            "total_dropped": float(self.total_dropped),
            "last_encode_ms": round(self.last_encode_duration_ms, 3),
            "avg_encode_ms": round(avg_ms, 3),
            "last_frame_kb": round(self.last_frame_bytes / 1024.0, 2),
        }

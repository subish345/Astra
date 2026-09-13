"""Unit tests for ColorSpatialObjectDetector on synthetic color patches."""

from datetime import datetime, timezone
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.perception.detection.color_adapter import ColorSpatialObjectDetector


def test_color_detector_red_and_yellow_boxes():
    """Verify detection of distinct colored patches."""
    detector = ColorSpatialObjectDetector(min_area=500.0)

    # Create synthetic frame with red box and yellow box
    img = np.zeros((480, 640, 3), dtype=np.uint8)

    # Red box patch in BGR: (B=0, G=0, R=255) -> (100, 100) to (180, 180) (area 6400)
    img[100:180, 100:180] = (0, 0, 255)

    # Yellow box patch in BGR: (B=0, G=255, R=255) -> (300, 200) to (380, 280)
    img[200:280, 300:380] = (0, 255, 255)

    fd = FrameData(
        frame_id=1,
        image=img,
        timestamp_mono=1.0,
        timestamp_wall=datetime.now(timezone.utc),
        source_id="synthetic",
    )

    detections = detector.detect(fd)
    classes_found = {d.class_name for d in detections}

    assert "RED_BOX" in classes_found
    assert "YELLOW_BOX" in classes_found
    assert len(detections) >= 2

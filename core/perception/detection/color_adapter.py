"""Deterministic color and spatial contour detector for ASTRA-EA experiment objects.

Provides a robust, 100% offline computer-vision baseline for recognizing the 4 core
demonstration objects (RED_BOX, YELLOW_BOX, MAIN_BOX, ASTRONAUT) via HSV color segmentation
and spatial morphology without external weights.
"""

from __future__ import annotations

from typing import Dict, List, Tuple
import cv2
import numpy as np

from core.camera.interface import FrameData
from core.perception.detection.interface import ObjectDetector
from core.perception.types import BoundingBox, Detection


class ColorSpatialObjectDetector(ObjectDetector):
    """Deterministic color-space and morphological detector for experiment items."""

    # HSV thresholds: (lower_bound, upper_bound)
    HSV_PROFILES: Dict[str, List[Tuple[np.ndarray, np.ndarray]]] = {
        "RED_BOX": [
            (np.array([0, 100, 70]), np.array([10, 255, 255])),
            (np.array([170, 100, 70]), np.array([180, 255, 255])),
        ],
        "YELLOW_BOX": [
            (np.array([20, 90, 90]), np.array([35, 255, 255])),
        ],
        "MAIN_BOX": [
            (np.array([100, 80, 60]), np.array([130, 255, 255])),  # Blue container
        ],
        "ASTRONAUT": [
            (np.array([0, 25, 60]), np.array([25, 170, 255])),   # Skin / upper torso
        ],
    }

    def __init__(
        self,
        min_area: float = 1200.0,
        max_area_ratio: float = 0.85,
        target_classes: List[str] = None,
    ):
        self.min_area = min_area
        self.max_area_ratio = max_area_ratio
        self.classes = target_classes or ["RED_BOX", "YELLOW_BOX", "MAIN_BOX", "ASTRONAUT"]

    def detect(self, frame: FrameData) -> List[Detection]:
        """Detect objects by color segmentation and contour analysis."""
        img = frame.image
        h, w = img.shape[:2]
        total_frame_area = float(h * w)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Apply gentle blur to smooth sensor noise
        blurred = cv2.GaussianBlur(hsv, (5, 5), 0)

        detections: List[Detection] = []

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        for class_name in self.classes:
            if class_name not in self.HSV_PROFILES:
                continue

            # Accumulate mask for this class
            class_mask = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in self.HSV_PROFILES[class_name]:
                mask = cv2.inRange(blurred, lower, upper)
                class_mask = cv2.bitwise_or(class_mask, mask)

            # Morphological opening and closing
            opened = cv2.morphologyEx(class_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=2)

            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < self.min_area or (area / total_frame_area) > self.max_area_ratio:
                    continue

                x, y, cw, ch = cv2.boundingRect(cnt)

                # Confidence based on contour solidity and area prominence
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                solidity = (area / hull_area) if hull_area > 0 else 0.5
                confidence = float(np.clip(0.65 + 0.30 * solidity, 0.5, 0.96))

                bbox = BoundingBox(
                    x1=float(x),
                    y1=float(y),
                    x2=float(x + cw),
                    y2=float(y + ch),
                )

                detections.append(
                    Detection(
                        class_name=class_name,
                        confidence=round(confidence, 3),
                        bbox=bbox,
                        timestamp=frame.timestamp_mono,
                        frame_id=frame.frame_id,
                        source="COLOR_SPATIAL",
                    )
                )

        return detections

    def get_supported_classes(self) -> List[str]:
        return list(self.classes)

    @property
    def model_name(self) -> str:
        return "ColorSpatialObjectDetector"

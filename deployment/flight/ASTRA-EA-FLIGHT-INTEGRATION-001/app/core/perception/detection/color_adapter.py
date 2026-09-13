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
            (np.array([0, 115, 70]), np.array([10, 255, 255])),
            (np.array([170, 115, 70]), np.array([180, 255, 255])),
        ],
        "YELLOW_BOX": [
            (np.array([20, 105, 100]), np.array([35, 255, 255])),
        ],
        "MAIN_BOX": [
            (np.array([100, 95, 60]), np.array([130, 255, 255])),  # Blue container
        ],
    }

    def __init__(
        self,
        min_area: float = 800.0,
        max_area_ratio: float = 0.85,
        target_classes: List[str] = None,
    ):
        self.min_area = min_area
        self.max_area_ratio = max_area_ratio
        self.classes = target_classes or ["RED_BOX", "YELLOW_BOX", "MAIN_BOX", "ASTRONAUT"]

        # Optional face cascade for grounding the ASTRONAUT class without false-positive wall colors
        self._face_cascade = None
        for candidate_path in [
            "models/checkpoints/haarcascade_frontalface_default.xml",
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml" if hasattr(cv2, "data") else "",
        ]:
            if candidate_path and cv2.os.path.exists(candidate_path):
                cascade = cv2.CascadeClassifier(candidate_path)
                if not cascade.empty():
                    self._face_cascade = cascade
                    break

    def detect(self, frame: FrameData) -> List[Detection]:
        """Detect objects by color segmentation and contour analysis."""
        img = frame.image
        h, w = img.shape[:2]
        total_frame_area = float(h * w)

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        blurred = cv2.GaussianBlur(hsv, (5, 5), 0)

        detections: List[Detection] = []
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

        for class_name in self.classes:
            # Case 1: ASTRONAUT grounded by human face/upper-body cascade
            if class_name == "ASTRONAUT":
                if self._face_cascade is not None:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = self._face_cascade.detectMultiScale(
                        gray, scaleFactor=1.15, minNeighbors=4, minSize=(60, 60)
                    )
                    for fx, fy, fw, fh in faces:
                        # Expand face bbox to upper torso
                        x1 = max(0.0, float(fx - int(fw * 0.35)))
                        y1 = max(0.0, float(fy - int(fh * 0.2)))
                        x2 = min(float(w), float(fx + int(fw * 1.35)))
                        y2 = min(float(h), float(fy + int(fh * 2.8)))
                        detections.append(
                            Detection(
                                class_name="ASTRONAUT",
                                confidence=0.91,
                                bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                                timestamp=frame.timestamp_mono,
                                frame_id=frame.frame_id,
                                source="HAAR_ASTRONAUT",
                            )
                        )
                continue

            # Case 2: Colored experiment objects
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
                confidence = float(np.clip(0.68 + 0.28 * solidity, 0.5, 0.98))

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

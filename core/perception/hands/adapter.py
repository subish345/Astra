"""Lightweight hand detector adapter for ASTRA-EA.

Extracts hand regions, wrist anchors, and finger keypoint approximations using
YCrCb skin segmentation and contour defect geometry without external cloud models.
"""

from __future__ import annotations

from typing import List, Tuple
import cv2
import numpy as np

from core.camera.interface import FrameData
from core.perception.hands.interface import HandDetector
from core.perception.types import BoundingBox, HandObservation, HandType, Keypoint


class LightweightHandDetector(HandDetector):
    """Local, offline hand and wrist detector based on skin-space morphology."""

    def __init__(self, min_hand_area: float = 4800.0, max_hands: int = 2):
        self.min_hand_area = min_hand_area
        self.max_hands = max_hands

    def detect(self, frame: FrameData) -> List[HandObservation]:
        """Detect hands, wrist location, and fingertip keypoints using dual-space skin geometry."""
        img = frame.image
        h, w = img.shape[:2]

        # 1. Dual-space illumination-tolerant skin filtering: YCrCb + HSV
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        mask_ycrcb = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_hsv1 = cv2.inRange(hsv, np.array([0, 50, 60]), np.array([20, 200, 255]))
        mask_hsv2 = cv2.inRange(hsv, np.array([170, 50, 60]), np.array([180, 200, 255]))
        mask_hsv = cv2.bitwise_or(mask_hsv1, mask_hsv2)

        combined = cv2.bitwise_and(mask_ycrcb, mask_hsv)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_hand_area or area > 26000.0:
                continue
            x, y, cw, ch = cv2.boundingRect(c)
            # Filter out top-edge ceiling reflections and oversized bounds
            if y <= 15 or cw > 220 or ch > 250:
                continue
            aspect = float(cw) / ch if ch > 0 else 0
            if not (0.38 <= aspect <= 1.85):
                continue
            valid_contours.append(c)

        # Sort by area descending
        valid_contours = sorted(valid_contours, key=cv2.contourArea, reverse=True)[: self.max_hands]

        hands: List[HandObservation] = []
        frame_center_x = w / 2.0

        for cnt in valid_contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            palm_cx = x + cw / 2.0
            palm_cy = y + ch / 2.0

            # Estimate wrist as bottom center of bounding box
            wrist_x = palm_cx
            wrist_y = float(y + ch)

            # Left vs Right heuristic based on frame relative x-axis
            hand_type = HandType.LEFT if palm_cx < frame_center_x else HandType.RIGHT

            # Compute fingertip landmarks using convex hull extremities
            hull = cv2.convexHull(cnt, returnPoints=True)
            keypoints = [
                Keypoint(x=wrist_x, y=wrist_y, confidence=0.85, name="wrist"),
                Keypoint(x=palm_cx, y=palm_cy, confidence=0.88, name="palm_center"),
            ]

            # Pick highest point as primary fingertip
            highest_pt = min(hull, key=lambda pt: pt[0][1])[0]
            keypoints.append(
                Keypoint(x=float(highest_pt[0]), y=float(highest_pt[1]), confidence=0.78, name="primary_fingertip")
            )

            bbox = BoundingBox(
                x1=float(x),
                y1=float(y),
                x2=float(x + cw),
                y2=float(y + ch),
            )

            hands.append(
                HandObservation(
                    hand_type=hand_type,
                    keypoints=keypoints,
                    confidence=0.82,
                    wrist=(wrist_x, wrist_y),
                    bbox=bbox,
                    source="LIGHTWEIGHT_HANDS",
                )
            )

        return hands

    @property
    def model_name(self) -> str:
        return "LightweightHandDetector"


class StubHandDetector(HandDetector):
    """Development test double for hand detection."""

    def __init__(self, predefined_hands: List[HandObservation] = None):
        self.predefined = predefined_hands or []

    def detect(self, frame: FrameData) -> List[HandObservation]:
        return [
            HandObservation(
                hand_type=h.hand_type,
                keypoints=h.keypoints,
                confidence=h.confidence,
                wrist=h.wrist,
                bbox=h.bbox,
                source="TEST MOCK",
            )
            for h in self.predefined
        ]

    @property
    def model_name(self) -> str:
        return "StubHandDetector"

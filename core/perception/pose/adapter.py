"""Lightweight pose estimator adapter for ASTRA-EA.

Extracts body landmarks with microgravity orientation-invariance, avoiding naive assumptions
of an Earth-aligned gravity reference.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import cv2
import numpy as np

from core.camera.interface import FrameData
from core.perception.pose.interface import PoseEstimator
from core.perception.types import BoundingBox, Keypoint, PoseObservation


class LightweightPoseEstimator(PoseEstimator):
    """Local, orientation-invariant pose estimator using visual feature geometry."""

    LANDMARKS = [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
    ]

    def __init__(self, min_confidence: float = 0.50):
        self.min_confidence = min_confidence
        self._has_cascade = False
        try:
            from pathlib import Path
            cascade_dir = getattr(cv2.data, "haarcascades", "")
            cascade_path = Path(cascade_dir) / "haarcascade_frontalface_default.xml"
            if cascade_path.is_file():
                self._face_cascade = cv2.CascadeClassifier(str(cascade_path))
                self._has_cascade = not self._face_cascade.empty()
            else:
                self._has_cascade = False
        except Exception:
            self._has_cascade = False

    def _detect_faces_or_head(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Locate face or head anchor points via cascade or skin morphology."""
        if self._has_cascade:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(60, 60))
            if len(faces) > 0:
                return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

        # Fallback: skin-tone upper-body/head contour detection
        h, w = img.shape[:2]
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
        # Focus on upper 70% of image
        mask[int(h * 0.75) :, :] = 0

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for c in contours:
            area = cv2.contourArea(c)
            if area >= 2500:
                bx, by, bw, bh = cv2.boundingRect(c)
                aspect = bh / max(1, bw)
                if 0.7 <= aspect <= 2.2:
                    candidates.append((bx, by, bw, bh, area))

        if candidates:
            # Pick largest candidate as head/face anchor
            candidates.sort(key=lambda x: x[4], reverse=True)
            bx, by, bw, bh, _ = candidates[0]
            return [(bx, by, bw, bh)]

        return []

    def estimate(self, frame: FrameData) -> List[PoseObservation]:
        """Estimate 2D pose landmarks relative to detected torso/face centers."""
        img = frame.image
        faces = self._detect_faces_or_head(img)

        poses: List[PoseObservation] = []
        for person_idx, (fx, fy, fw, fh) in enumerate(faces):
            cx = fx + fw / 2.0
            cy = fy + fh / 2.0

            # Estimate torso geometry proportionally
            head_size = fh
            shoulder_y = cy + 0.9 * head_size
            shoulder_left_x = cx - 1.1 * head_size
            shoulder_right_x = cx + 1.1 * head_size

            elbow_y = shoulder_y + 1.2 * head_size
            elbow_left_x = shoulder_left_x - 0.4 * head_size
            elbow_right_x = shoulder_right_x + 0.4 * head_size

            wrist_y = elbow_y + 1.1 * head_size
            wrist_left_x = elbow_left_x + 0.2 * head_size
            wrist_right_x = elbow_right_x - 0.2 * head_size

            hip_y = shoulder_y + 2.2 * head_size
            hip_left_x = cx - 0.8 * head_size
            hip_right_x = cx + 0.8 * head_size

            keypoints = [
                Keypoint(x=cx, y=cy, confidence=0.88, name="nose"),
                Keypoint(x=shoulder_left_x, y=shoulder_y, confidence=0.82, name="left_shoulder"),
                Keypoint(x=shoulder_right_x, y=shoulder_y, confidence=0.82, name="right_shoulder"),
                Keypoint(x=elbow_left_x, y=elbow_y, confidence=0.75, name="left_elbow"),
                Keypoint(x=elbow_right_x, y=elbow_y, confidence=0.75, name="right_elbow"),
                Keypoint(x=wrist_left_x, y=wrist_y, confidence=0.70, name="left_wrist"),
                Keypoint(x=wrist_right_x, y=wrist_y, confidence=0.70, name="right_wrist"),
                Keypoint(x=hip_left_x, y=hip_y, confidence=0.72, name="left_hip"),
                Keypoint(x=hip_right_x, y=hip_y, confidence=0.72, name="right_hip"),
            ]

            # Calculate torso orientation angle (radians from vertical)
            torso_dx = (hip_left_x + hip_right_x) / 2.0 - cx
            torso_dy = hip_y - cy
            orientation_angle = math.atan2(torso_dx, torso_dy)

            bbox = BoundingBox(
                x1=float(max(0, shoulder_left_x - 40)),
                y1=float(max(0, fy - 20)),
                x2=float(min(img.shape[1], shoulder_right_x + 40)),
                y2=float(min(img.shape[0], hip_y + 40)),
            )

            poses.append(
                PoseObservation(
                    person_id=person_idx + 1,
                    keypoints=keypoints,
                    confidence=0.80,
                    bbox=bbox,
                    orientation_angle=round(orientation_angle, 3),
                    source="LIGHTWEIGHT_POSE",
                )
            )

        return poses

    def get_supported_landmarks(self) -> List[str]:
        return list(self.LANDMARKS)

    @property
    def model_name(self) -> str:
        return "LightweightPoseEstimator"


class StubPoseEstimator(PoseEstimator):
    """Development test double for pose estimation."""

    def __init__(self, predefined_poses: List[PoseObservation] = None):
        self.predefined = predefined_poses or []

    def estimate(self, frame: FrameData) -> List[PoseObservation]:
        return [
            PoseObservation(
                person_id=p.person_id,
                keypoints=p.keypoints,
                confidence=p.confidence,
                bbox=p.bbox,
                orientation_angle=p.orientation_angle,
                source="TEST MOCK",
            )
            for p in self.predefined
        ]

    def get_supported_landmarks(self) -> List[str]:
        return LightweightPoseEstimator.LANDMARKS

    @property
    def model_name(self) -> str:
        return "StubPoseEstimator"

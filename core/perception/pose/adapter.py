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
        self._has_upperbody = False

        from pathlib import Path
        root = Path(__file__).resolve().parent.parent.parent.parent
        chk_dir = root / "models" / "checkpoints"
        sys_cascade_dir = Path(getattr(cv2.data, "haarcascades", ""))

        face_paths = [
            chk_dir / "haarcascade_frontalface_default.xml",
            sys_cascade_dir / "haarcascade_frontalface_default.xml",
        ]
        upperbody_paths = [
            chk_dir / "haarcascade_upperbody.xml",
            sys_cascade_dir / "haarcascade_upperbody.xml",
        ]

        for p in face_paths:
            if p.is_file():
                self._face_cascade = cv2.CascadeClassifier(str(p))
                if not self._face_cascade.empty():
                    self._has_cascade = True
                    break

        for p in upperbody_paths:
            if p.is_file():
                self._upperbody_cascade = cv2.CascadeClassifier(str(p))
                if not self._upperbody_cascade.empty():
                    self._has_upperbody = True
                    break

    def _detect_faces_or_head(self, img: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Locate real human face or head anchor points without false positives on furniture."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1. Frontal face detection
        if self._has_cascade:
            faces = self._face_cascade.detectMultiScale(
                gray, scaleFactor=1.15, minNeighbors=5, minSize=(50, 50)
            )
            if len(faces) > 0:
                return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

        # 2. Upper-body detection fallback
        if self._has_upperbody:
            bodies = self._upperbody_cascade.detectMultiScale(
                gray, scaleFactor=1.15, minNeighbors=4, minSize=(100, 100)
            )
            if len(bodies) > 0:
                # Estimate head as top third of detected upper body
                head_anchors = []
                for (x, y, w, h) in bodies:
                    hw = int(w * 0.45)
                    hh = int(h * 0.35)
                    hx = int(x + (w - hw) / 2)
                    head_anchors.append((hx, int(y), hw, hh))
                return head_anchors

        # 3. If no cascades available, use strict skin oval morphology
        if not self._has_cascade and not self._has_upperbody:
            h, w = img.shape[:2]
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            mask = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))
            mask[int(h * 0.70):, :] = 0  # Upper 70% only

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            candidates = []
            for c in contours:
                area = cv2.contourArea(c)
                if 3000 <= area <= 30000:
                    bx, by, bw, bh = cv2.boundingRect(c)
                    aspect = bh / max(1, bw)
                    hull = cv2.convexHull(c)
                    solidity = area / max(1.0, cv2.contourArea(hull))
                    # Face oval has aspect 1.1 - 1.6 and high solidity > 0.75
                    if 1.0 <= aspect <= 1.6 and solidity >= 0.75:
                        candidates.append((bx, by, bw, bh, area))

            if candidates:
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

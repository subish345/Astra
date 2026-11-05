"""MediaPipe Anatomical Hand Detector Adapter for ASTRA-EA.

Extracts anatomical hand observations (wrist, palm center, thumb, index, pinky) directly
from 33-point BlazePose landmarks, ensuring biological left/right distinction invariant to
crossing the frame center line, illumination fluctuations, or glove materials.
Gracefully falls back to skin morphology when the full body skeleton is not in field of view.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np

from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.perception.hands.adapter import LightweightHandDetector
from core.perception.hands.interface import HandDetector
from core.perception.pose.mediapipe_adapter import MediaPipePoseEstimator
from core.perception.types import BoundingBox, HandObservation, HandType, Keypoint, PoseObservation

logger = get_logger("HANDS_MEDIAPIPE")


class MediaPipeHandDetector(HandDetector):
    """Anatomical hand detector extracting true left/right hand effectors from 3D pose."""

    def __init__(
        self,
        pose_estimator: Optional[MediaPipePoseEstimator] = None,
        min_hand_confidence: float = 0.40,
        enable_morphology_fallback: bool = True,
    ):
        self.min_hand_confidence = min_hand_confidence
        self.enable_morphology_fallback = enable_morphology_fallback
        self._pose_estimator = pose_estimator
        self._fallback_detector = LightweightHandDetector() if enable_morphology_fallback else None

    def detect(self, frame: FrameData, poses: Optional[List[PoseObservation]] = None) -> List[HandObservation]:
        """Extract hands from supplied pose observations or run pose estimation."""
        # 1. Use supplied poses or run pose estimator if available
        if poses is None and self._pose_estimator and self._pose_estimator.is_available:
            poses = self._pose_estimator.estimate(frame)

        hands: List[HandObservation] = []
        h, w = frame.image.shape[:2]

        if poses:
            for pose in poses:
                kp_dict = {kp.name: kp for kp in pose.keypoints if kp.name}

                # Evaluate Left Hand Effectors
                left_wrist = kp_dict.get("left_wrist")
                if left_wrist and left_wrist.confidence >= self.min_hand_confidence:
                    left_hand = self._build_hand(
                        HandType.LEFT,
                        left_wrist,
                        kp_dict.get("left_thumb"),
                        kp_dict.get("left_index"),
                        kp_dict.get("left_pinky"),
                        w, h,
                    )
                    if left_hand:
                        hands.append(left_hand)

                # Evaluate Right Hand Effectors
                right_wrist = kp_dict.get("right_wrist")
                if right_wrist and right_wrist.confidence >= self.min_hand_confidence:
                    right_hand = self._build_hand(
                        HandType.RIGHT,
                        right_wrist,
                        kp_dict.get("right_thumb"),
                        kp_dict.get("right_index"),
                        kp_dict.get("right_pinky"),
                        w, h,
                    )
                    if right_hand:
                        hands.append(right_hand)

        # 2. If no hands detected via pose (e.g. camera close-up on hands), fallback to morphology
        if not hands and self._fallback_detector:
            hands = self._fallback_detector.detect(frame)

        return hands

    def _build_hand(
        self,
        hand_type: HandType,
        wrist: Keypoint,
        thumb: Optional[Keypoint],
        index: Optional[Keypoint],
        pinky: Optional[Keypoint],
        frame_w: int,
        frame_h: int,
    ) -> Optional[HandObservation]:
        """Construct structured HandObservation with wrist, palm centroid, and finger web."""
        hand_keypoints = [
            Keypoint(x=wrist.x, y=wrist.y, z=wrist.z, confidence=wrist.confidence, name="wrist")
        ]
        pts_x = [wrist.x]
        pts_y = [wrist.y]

        if thumb:
            hand_keypoints.append(Keypoint(x=thumb.x, y=thumb.y, z=thumb.z, confidence=thumb.confidence, name="thumb"))
            pts_x.append(thumb.x)
            pts_y.append(thumb.y)
        if index:
            hand_keypoints.append(Keypoint(x=index.x, y=index.y, z=index.z, confidence=index.confidence, name="index"))
            pts_x.append(index.x)
            pts_y.append(index.y)
        if pinky:
            hand_keypoints.append(Keypoint(x=pinky.x, y=pinky.y, z=pinky.z, confidence=pinky.confidence, name="pinky"))
            pts_x.append(pinky.x)
            pts_y.append(pinky.y)

        # Compute palm centroid as mean of wrist and finger roots
        palm_x = float(np.mean(pts_x))
        palm_y = float(np.mean(pts_y))
        hand_keypoints.append(
            Keypoint(x=palm_x, y=palm_y, confidence=wrist.confidence, name="palm_center")
        )

        # Compute bounding box
        margin = max(35.0, float(np.ptp(pts_x)) * 0.8)
        bx1 = max(0.0, min(pts_x) - margin * 0.5)
        by1 = max(0.0, min(pts_y) - margin * 0.5)
        bx2 = min(float(frame_w), max(pts_x) + margin * 0.5)
        by2 = min(float(frame_h), max(pts_y) + margin * 0.5)
        bbox = BoundingBox(x1=bx1, y1=by1, x2=bx2, y2=by2)

        conf = float(np.mean([kp.confidence for kp in hand_keypoints]))

        return HandObservation(
            hand_type=hand_type,
            keypoints=hand_keypoints,
            confidence=round(conf, 2),
            wrist=(wrist.x, wrist.y),
            bbox=bbox,
            source="MEDIAPIPE_HAND",
        )

    @property
    def model_name(self) -> str:
        return "MediaPipeHandDetector (Pose-Derived Anatomical)"

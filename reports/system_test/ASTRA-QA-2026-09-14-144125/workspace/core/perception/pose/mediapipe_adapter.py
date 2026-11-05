"""MediaPipe 33-Keypoint Pose Estimator Adapter for ASTRA-EA.

Extracts complete 3D skeletal landmarks using Google MediaPipe PoseLandmarker Lite,
enabling true biokinematic articulation (shoulders, elbows, wrists, hips, knees, feet)
under microgravity orientation invariance and arbitrary astronaut postures.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple
import cv2
import math
import time
import numpy as np

from core.camera.interface import FrameData
from core.common.logging import get_logger
from core.perception.pose.interface import PoseEstimator
from core.perception.pose.smoothing import TemporalPoseSmoother
from core.perception.types import BoundingBox, Keypoint, PoseObservation

logger = get_logger("POSE_MEDIAPIPE")

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MP_AVAILABLE = True
except ImportError:
    MP_AVAILABLE = False
    logger.warning("MediaPipe library not installed. MediaPipePoseEstimator will operate in fallback mode.")


class MediaPipePoseEstimator(PoseEstimator):
    """Production 33-keypoint 3D skeletal pose estimator using MediaPipe Tasks."""

    LANDMARKS = [
        "nose",
        "left_eye_inner",
        "left_eye",
        "left_eye_outer",
        "right_eye_inner",
        "right_eye",
        "right_eye_outer",
        "left_ear",
        "right_ear",
        "mouth_left",
        "mouth_right",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_pinky",
        "right_pinky",
        "left_index",
        "right_index",
        "left_thumb",
        "right_thumb",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
        "left_heel",
        "right_heel",
        "left_foot_index",
        "right_foot_index",
    ]

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        min_detection_confidence: float = 0.50,
        min_tracking_confidence: float = 0.50,
        enable_smoothing: bool = True,
        delegate: str = "cpu",
    ):
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.enable_smoothing = enable_smoothing
        self.smoother = TemporalPoseSmoother() if enable_smoothing else None
        self.detector = None
        self.device_used = "NONE"
        self._is_ready = False

        if not MP_AVAILABLE:
            return

        # Resolve model path
        if model_path is None:
            root = Path(__file__).resolve().parent.parent.parent.parent
            model_path = root / "models" / "checkpoints" / "pose_landmarker_lite.task"
        else:
            model_path = Path(model_path)

        if not model_path.is_file():
            logger.warning(f"MediaPipe task asset not found at {model_path}. MediaPipe disabled.")
            return

        # Initialize detector with GPU/CPU delegate
        if delegate.lower() == "gpu":
            try:
                base_options = python.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=python.BaseOptions.Delegate.GPU,
                )
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False,
                    min_pose_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
                self.device_used = "GPU"
                self._is_ready = True
                logger.info("MediaPipe 33-Keypoint PoseLandmarker initialized on GPU.")
            except Exception as exc:
                logger.warning(f"Failed to initialize MediaPipe PoseLandmarker on GPU, falling back to CPU: {exc}")

        if not self._is_ready:
            try:
                base_options = python.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=python.BaseOptions.Delegate.CPU,
                )
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False,
                    min_pose_detection_confidence=min_detection_confidence,
                    min_tracking_confidence=min_tracking_confidence,
                )
                self.detector = vision.PoseLandmarker.create_from_options(options)
                self.device_used = "CPU"
                self._is_ready = True
                logger.info("MediaPipe 33-Keypoint PoseLandmarker initialized on CPU (XNNPACK).")
            except Exception as exc:
                logger.error(f"Failed to initialize MediaPipe PoseLandmarker on CPU: {exc}")

    @property
    def is_available(self) -> bool:
        return self._is_ready and self.detector is not None

    def estimate(self, frame: FrameData) -> List[PoseObservation]:
        """Extract 33 3D skeletal landmarks from the optical frame."""
        if not self.is_available:
            return []

        img = frame.image
        h, w = img.shape[:2]

        try:
            rgb_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.detector.detect(mp_image)
        except Exception as exc:
            logger.debug(f"MediaPipe inference failed: {exc}")
            return []

        if not detection_result.pose_landmarks:
            return []

        poses: List[PoseObservation] = []

        for person_idx, landmarks in enumerate(detection_result.pose_landmarks):
            keypoints: List[Keypoint] = []
            xs: List[float] = []
            ys: List[float] = []

            for i, lm in enumerate(landmarks):
                if i >= len(self.LANDMARKS):
                    break
                name = self.LANDMARKS[i]
                # Convert normalized coordinates [0.0, 1.0] to pixel space
                px = float(lm.x * w)
                py = float(lm.y * h)
                pz = float(lm.z * w) if getattr(lm, "z", None) is not None else None
                visibility = getattr(lm, "visibility", None)
                conf = float(visibility) if visibility is not None else 0.0

                keypoints.append(
                    Keypoint(
                        x=px,
                        y=py,
                        z=pz,
                        confidence=conf,
                        name=name,
                    )
                )
                xs.append(px)
                ys.append(py)

            if not keypoints:
                continue

            # Compute bounding box enclosing visible keypoints
            min_x = max(0.0, min(xs) - 20.0)
            max_x = min(float(w), max(xs) + 20.0)
            min_y = max(0.0, min(ys) - 20.0)
            max_y = min(float(h), max(ys) + 20.0)
            bbox = BoundingBox(x1=min_x, y1=min_y, x2=max_x, y2=max_y)

            # Compute orientation angle and roll from shoulder and hip vectors
            orientation_angle: Optional[float] = None
            kp_dict = {kp.name: kp for kp in keypoints if kp.name}
            if "left_shoulder" in kp_dict and "right_shoulder" in kp_dict:
                ls = kp_dict["left_shoulder"]
                rs = kp_dict["right_shoulder"]
                dx = rs.x - ls.x
                dy = rs.y - ls.y
                # Orientation angle relative to vertical
                orientation_angle = round(math.atan2(dx, dy), 3)

            avg_confidence = float(np.mean([kp.confidence for kp in keypoints]))

            poses.append(
                PoseObservation(
                    person_id=person_idx + 1,
                    keypoints=keypoints,
                    confidence=round(avg_confidence, 2),
                    bbox=bbox,
                    orientation_angle=orientation_angle,
                    source="MEDIAPIPE_33",
                )
            )

        # Apply adaptive temporal smoothing if enabled
        if self.smoother and poses:
            ts = getattr(frame, "timestamp_mono", time.time())
            poses = self.smoother.smooth(poses, timestamp=ts)

        return poses

    def get_supported_landmarks(self) -> List[str]:
        return list(self.LANDMARKS)

    @property
    def model_name(self) -> str:
        return f"MediaPipePoseEstimator ({self.device_used})"

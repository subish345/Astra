"""Unit tests for MediaPipe 33-point pose, anatomical hands, and temporal smoothing.
"""

from __future__ import annotations

from datetime import datetime, timezone
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.perception.hands.mediapipe_adapter import MediaPipeHandDetector
from core.perception.pose.mediapipe_adapter import MediaPipePoseEstimator
from core.perception.pose.smoothing import TemporalPoseSmoother
from core.perception.types import BoundingBox, HandType, Keypoint, PoseObservation


def _make_frame(img: np.ndarray, frame_id: int = 1) -> FrameData:
    return FrameData(
        frame_id=frame_id,
        image=img,
        timestamp_mono=float(frame_id) * 0.033,
        timestamp_wall=datetime.now(timezone.utc),
        source_id="test_cam",
    )


class TestMediaPipePoseEstimator:
    def test_initialization_and_landmarks(self):
        estimator = MediaPipePoseEstimator()
        assert estimator.is_available is True
        assert "MediaPipe" in estimator.model_name
        landmarks = estimator.get_supported_landmarks()
        assert len(landmarks) == 33
        assert "left_wrist" in landmarks
        assert "right_wrist" in landmarks
        assert "left_ankle" in landmarks
        assert "nose" in landmarks

    def test_missing_model_fallback(self, tmp_path):
        bad_path = tmp_path / "nonexistent.task"
        estimator = MediaPipePoseEstimator(model_path=bad_path)
        assert estimator.is_available is False
        assert estimator.estimate(_make_frame(np.zeros((100, 100, 3), dtype=np.uint8))) == []

    def test_estimate_blank_frame(self):
        estimator = MediaPipePoseEstimator()
        frame = _make_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        poses = estimator.estimate(frame)
        assert isinstance(poses, list)
        # Blank black frame should yield 0 poses
        assert len(poses) == 0


class TestTemporalPoseSmoother:
    def test_smoothing_reduces_noise(self):
        smoother = TemporalPoseSmoother(min_cutoff=0.05, beta=0.1)

        # Generate noisy 1D oscillation around x=100.0
        np.random.seed(42)
        raw_x_values = [100.0 + (5.0 if i % 2 == 0 else -5.0) for i in range(20)]
        smoothed_x_values = []

        for i, raw_x in enumerate(raw_x_values):
            kp = Keypoint(x=raw_x, y=200.0, confidence=0.9, name="left_wrist")
            pose = PoseObservation(person_id=1, keypoints=[kp], confidence=0.9)
            res = smoother.smooth([pose], timestamp=float(i) * 0.033)
            smoothed_x_values.append(res[0].keypoints[0].x)

        # Variance of smoothed values must be strictly less than raw noisy values
        raw_var = np.var(raw_x_values)
        smoothed_var = np.var(smoothed_x_values[5:])  # Skip warm-up
        assert smoothed_var < raw_var

    def test_smoother_reset(self):
        smoother = TemporalPoseSmoother()
        kp = Keypoint(x=150.0, y=150.0, confidence=0.9, name="nose")
        pose = PoseObservation(person_id=1, keypoints=[kp], confidence=0.9)
        smoother.smooth([pose], timestamp=0.0)
        assert len(smoother._states) > 0
        smoother.reset()
        assert len(smoother._states) == 0


class TestMediaPipeHandDetector:
    def test_detect_from_pose_landmarks(self):
        detector = MediaPipeHandDetector(enable_morphology_fallback=False)

        kps = [
            Keypoint(x=120.0, y=200.0, confidence=0.95, name="left_wrist"),
            Keypoint(x=130.0, y=190.0, confidence=0.90, name="left_thumb"),
            Keypoint(x=140.0, y=185.0, confidence=0.92, name="left_index"),
            Keypoint(x=145.0, y=195.0, confidence=0.88, name="left_pinky"),
            Keypoint(x=350.0, y=200.0, confidence=0.95, name="right_wrist"),
            Keypoint(x=360.0, y=190.0, confidence=0.90, name="right_thumb"),
            Keypoint(x=370.0, y=185.0, confidence=0.92, name="right_index"),
            Keypoint(x=375.0, y=195.0, confidence=0.88, name="right_pinky"),
        ]
        pose = PoseObservation(person_id=1, keypoints=kps, confidence=0.92, bbox=BoundingBox(100, 150, 400, 300))
        frame = _make_frame(np.zeros((480, 640, 3), dtype=np.uint8))

        hands = detector.detect(frame, poses=[pose])
        assert len(hands) == 2

        # Verify anatomical left hand
        left = next(h for h in hands if h.hand_type == HandType.LEFT)
        assert left.wrist == (120.0, 200.0)
        assert any(kp.name == "palm_center" for kp in left.keypoints)
        assert left.bbox is not None
        assert left.bbox.x1 < 120.0 < left.bbox.x2

        # Verify anatomical right hand
        right = next(h for h in hands if h.hand_type == HandType.RIGHT)
        assert right.wrist == (350.0, 200.0)
        assert any(kp.name == "palm_center" for kp in right.keypoints)

    def test_detect_anatomical_left_on_right_side(self):
        """Cross-body reach: left hand reaches over to right half of screen (x > 320)."""
        detector = MediaPipeHandDetector(enable_morphology_fallback=False)

        kps = [
            Keypoint(x=500.0, y=200.0, confidence=0.95, name="left_wrist"),
            Keypoint(x=510.0, y=190.0, confidence=0.90, name="left_thumb"),
        ]
        pose = PoseObservation(person_id=1, keypoints=kps, confidence=0.95)
        frame = _make_frame(np.zeros((480, 640, 3), dtype=np.uint8))

        hands = detector.detect(frame, poses=[pose])
        assert len(hands) == 1
        # Crucial test: despite x=500 (right side of 640px frame), hand must be anatomical LEFT
        assert hands[0].hand_type == HandType.LEFT

    def test_morphology_fallback_when_no_pose(self):
        detector = MediaPipeHandDetector(enable_morphology_fallback=True)
        # Blank frame produces no morphology hands either, but completes cleanly without exception
        frame = _make_frame(np.zeros((480, 640, 3), dtype=np.uint8))
        hands = detector.detect(frame, poses=[])
        assert isinstance(hands, list)

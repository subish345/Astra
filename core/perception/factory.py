"""Shared runtime selection of the installed pose and hand adapters."""
from core.common.logging import get_logger


def create_pose_and_hand_detectors():
    from core.perception.pose.mediapipe_adapter import MediaPipePoseEstimator
    from core.perception.hands.mediapipe_adapter import MediaPipeHandDetector

    pose = MediaPipePoseEstimator()
    if pose.is_available:
        return pose, MediaPipeHandDetector(pose_estimator=pose)
    get_logger("PERCEPTION").warning(
        "33-point pose unavailable; using legacy pose/hand fallback (degraded capability)."
    )
    from core.perception.pose.adapter import LightweightPoseEstimator
    from core.perception.hands.adapter import LightweightHandDetector
    return LightweightPoseEstimator(), LightweightHandDetector()

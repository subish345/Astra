# ==============================================================================
# ASTRA-EA Normalized Spatial Reasoning & Anatomical Hand Grounding
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Normalized spatial relationships and viewpoint-invariant anatomical hand reasoning.

Ensures spatial reasoning relies on relative geometry, object-to-object distances,
and anatomical keypoints rather than absolute camera-side coordinates or image-space left/right.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
from core.perception.types import BoundingBox, HandObservation, HandType, Keypoint, PoseObservation
from core.camera.profile import CameraProfile, CameraViewpoint


class SpatialGeometry:
    """Normalized spatial calculations invariant to camera viewpoint transformations."""

    @staticmethod
    def normalize_box(box: BoundingBox, frame_width: float, frame_height: float) -> BoundingBox:
        """Normalize bounding box coordinates into [0.0, 1.0] domain."""
        if frame_width <= 0 or frame_height <= 0:
            return box
        return BoundingBox(
            x1=max(0.0, min(1.0, box.x1 / frame_width)),
            y1=max(0.0, min(1.0, box.y1 / frame_height)),
            x2=max(0.0, min(1.0, box.x2 / frame_width)),
            y2=max(0.0, min(1.0, box.y2 / frame_height)),
            confidence=box.confidence,
            class_name=box.class_name,
            track_id=box.track_id,
        )

    @staticmethod
    def center(box: BoundingBox) -> Tuple[float, float]:
        """Compute the centroid of a bounding box."""
        return ((box.x1 + box.x2) / 2.0, (box.y1 + box.y2) / 2.0)

    @staticmethod
    def euclidean_distance(pt1: Tuple[float, float], pt2: Tuple[float, float]) -> float:
        """Compute Euclidean distance between two points."""
        return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

    @classmethod
    def relative_object_distance(cls, box_a: BoundingBox, box_b: BoundingBox) -> float:
        """Compute distance between centers of two objects normalized by average scale."""
        c1 = cls.center(box_a)
        c2 = cls.center(box_b)
        return cls.euclidean_distance(c1, c2)

    @classmethod
    def containment_ratio(cls, inner: BoundingBox, outer: BoundingBox) -> float:
        """Fraction of inner box area contained within outer box."""
        inter_x1 = max(inner.x1, outer.x1)
        inter_y1 = max(inner.y1, outer.y1)
        inter_x2 = min(inner.x2, outer.x2)
        inter_y2 = min(inner.y2, outer.y2)

        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0

        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        inner_area = max(1e-6, inner.area)
        return float(inter_area / inner_area)

    @classmethod
    def relative_relationships(cls, obj_a: BoundingBox, obj_b: BoundingBox) -> Dict[str, float | str | bool]:
        """Viewpoint-invariant geometric relationships between two objects."""
        c_a = cls.center(obj_a)
        c_b = cls.center(obj_b)
        dist = cls.euclidean_distance(c_a, c_b)
        iou = obj_a.iou(obj_b)
        contained = cls.containment_ratio(obj_a, obj_b) > 0.65

        dx = c_b[0] - c_a[0]
        dy = c_b[1] - c_a[1]

        # Invariant classification based on relative offset
        if contained:
            relation = "CONTAINED_IN"
        elif iou > 0.15 or dist < 0.15:
            relation = "CONTACT"
        elif dist < 0.35:
            relation = "PROXIMATE"
        else:
            relation = "DISTANT"

        return {
            "distance": float(dist),
            "iou": float(iou),
            "relation": relation,
            "relative_vector": (dx, dy),
        }


def ground_hand_anatomical(
    hand: HandObservation,
    poses: List[PoseObservation],
    camera_profile: Optional[CameraProfile] = None,
    max_wrist_dist: float = 0.35,
) -> HandType:
    """Ground hand observation to anatomical LEFT/RIGHT using body pose landmarks.

    CRITICAL PRINCIPLE:
    Avoid confusing image-space left/right with anatomical left/right.
    Associates the hand with the closest astronaut wrist keypoint (left_wrist vs right_wrist).
    If no wrist keypoints are visible, or the association is ambiguous, returns HAND_UNKNOWN.
    Never fabricates handedness based on image coordinates.
    """
    if not poses:
        # Without pose context, if hand already has an established anatomical identity, preserve it;
        # otherwise return UNKNOWN to avoid fabrication.
        return hand.hand_type if hand.hand_type != HandType.UNKNOWN else HandType.UNKNOWN

    hand_center = (
        (hand.bbox.x1 + hand.bbox.x2) / 2.0 if hand.bbox else 0.5,
        (hand.bbox.y1 + hand.bbox.y2) / 2.0 if hand.bbox else 0.5,
    )
    if hand.wrist:
        hand_center = hand.wrist

    best_hand_type = HandType.UNKNOWN
    min_dist = float("inf")
    second_min_dist = float("inf")

    for pose in poses:
        # Locate left and right wrist keypoints in pose
        left_wrist_kp: Optional[Keypoint] = None
        right_wrist_kp: Optional[Keypoint] = None

        for kp in pose.keypoints:
            name_lower = (kp.name or "").lower()
            if "left_wrist" in name_lower and kp.confidence >= 0.4:
                left_wrist_kp = kp
            elif "right_wrist" in name_lower and kp.confidence >= 0.4:
                right_wrist_kp = kp

        if left_wrist_kp:
            dist_l = math.hypot(hand_center[0] - left_wrist_kp.x, hand_center[1] - left_wrist_kp.y)
            if dist_l < min_dist:
                second_min_dist = min_dist
                min_dist = dist_l
                best_hand_type = HandType.LEFT
            elif dist_l < second_min_dist:
                second_min_dist = dist_l

        if right_wrist_kp:
            dist_r = math.hypot(hand_center[0] - right_wrist_kp.x, hand_center[1] - right_wrist_kp.y)
            if dist_r < min_dist:
                second_min_dist = min_dist
                min_dist = dist_r
                best_hand_type = HandType.RIGHT
            elif dist_r < second_min_dist:
                second_min_dist = dist_r

    # Association validity checks:
    # 1. Must be within spatial proximity threshold
    if min_dist > max_wrist_dist:
        return HandType.UNKNOWN

    # 2. Must not be ambiguous (min_dist must be distinctly closer than second_min_dist)
    if second_min_dist < float("inf") and (second_min_dist - min_dist) < 0.05:
        # Too close to call unambiguously
        return HandType.UNKNOWN

    return best_hand_type

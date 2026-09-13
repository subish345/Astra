"""Geometric and kinematic calculations for hand-object spatial relationships.

Provides pure functions for Euclidean distance, normalized distance, bounding box
overlap, quadrant bearings, velocity vectors, and motion cosine similarity.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from core.perception.types import BoundingBox


def calculate_pixel_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance in pixels between two 2D points."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def calculate_normalized_distance(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    frame_width: float = 640.0,
    frame_height: float = 480.0,
) -> float:
    """Calculate Euclidean distance normalized by the image diagonal."""
    diag = math.hypot(frame_width, frame_height)
    if diag <= 0.0:
        return 0.0
    return calculate_pixel_distance(p1, p2) / diag


def calculate_box_overlap_iou(box1: Optional[BoundingBox], box2: Optional[BoundingBox]) -> float:
    """Compute Intersection-over-Union (IoU) between two bounding boxes."""
    if box1 is None or box2 is None:
        return 0.0
    return box1.iou(box2)


def is_point_inside_box(point: Tuple[float, float], box: BoundingBox) -> bool:
    """Check whether a 2D point lies within a bounding box."""
    x, y = point
    return box.x1 <= x <= box.x2 and box.y1 <= y <= box.y2


def determine_relative_position(
    hand_pt: Tuple[float, float],
    obj_box: BoundingBox,
) -> str:
    """Determine the relative spatial orientation of a hand relative to an object."""
    if is_point_inside_box(hand_pt, obj_box):
        return "INSIDE"

    hx, hy = hand_pt
    ox, oy = obj_box.center
    dx = hx - ox
    dy = hy - oy

    if abs(dx) > abs(dy):
        return "RIGHT" if dx > 0 else "LEFT"
    else:
        return "BELOW" if dy > 0 else "ABOVE"


def compute_velocity_vector(
    p_curr: Tuple[float, float],
    p_prev: Tuple[float, float],
    dt: float,
) -> Tuple[float, float]:
    """Compute instantaneous 2D velocity vector (pixels per second)."""
    if dt <= 0.0001:
        return (0.0, 0.0)
    vx = (p_curr[0] - p_prev[0]) / dt
    vy = (p_curr[1] - p_prev[1]) / dt
    return (round(vx, 2), round(vy, 2))


def compute_motion_correlation(
    v1: Tuple[float, float],
    v2: Tuple[float, float],
    min_speed: float = 5.0,
) -> float:
    """Compute cosine similarity of two velocity vectors in [-1.0, 1.0].

    Returns 1.0 when perfectly coupled and co-directional, 0.0 when orthogonal or stationary,
    and -1.0 when moving in opposing directions.
    """
    speed1 = math.hypot(v1[0], v1[1])
    speed2 = math.hypot(v2[0], v2[1])

    # If either entity is essentially stationary, motion correlation is 0.0
    if speed1 < min_speed or speed2 < min_speed:
        return 0.0

    dot = (v1[0] * v2[0]) + (v1[1] * v2[1])
    denom = speed1 * speed2
    if denom <= 1e-6:
        return 0.0

    val = dot / denom
    # Clamp due to floating point precision
    return max(-1.0, min(1.0, round(val, 3)))


def compute_approach_speed(
    d_curr: float,
    d_prev: float,
    dt: float,
) -> float:
    """Compute rate of change of normalized distance (units per second).

    Negative values denote approach (distance decreasing); positive denote separation.
    """
    if dt <= 0.0001:
        return 0.0
    return round((d_curr - d_prev) / dt, 3)

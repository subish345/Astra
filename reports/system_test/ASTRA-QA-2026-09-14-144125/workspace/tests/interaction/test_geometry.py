"""Unit tests for spatial geometry and kinematic calculations."""

import math
import pytest
from core.interaction.geometry import (
    calculate_box_overlap_iou,
    calculate_normalized_distance,
    calculate_pixel_distance,
    compute_approach_speed,
    compute_motion_correlation,
    compute_velocity_vector,
    determine_relative_position,
    is_point_inside_box,
)
from core.perception.types import BoundingBox


def test_calculate_pixel_and_normalized_distance():
    p1 = (100.0, 100.0)
    p2 = (130.0, 140.0)
    dist = calculate_pixel_distance(p1, p2)
    assert dist == pytest.approx(50.0)

    # Diagonal of 640x480 is 800.0
    norm_dist = calculate_normalized_distance(p1, p2, 640.0, 480.0)
    assert norm_dist == pytest.approx(50.0 / 800.0)


def test_calculate_box_overlap_iou():
    box1 = BoundingBox(x1=0.0, y1=0.0, x2=10.0, y2=10.0)
    box2 = BoundingBox(x1=5.0, y1=0.0, x2=15.0, y2=10.0)
    # Intersection = 5 * 10 = 50, Union = 100 + 100 - 50 = 150 -> IoU = 1/3
    iou = calculate_box_overlap_iou(box1, box2)
    assert iou == pytest.approx(1.0 / 3.0, rel=1e-2)

    # Non-overlapping
    box3 = BoundingBox(x1=20.0, y1=20.0, x2=30.0, y2=30.0)
    assert calculate_box_overlap_iou(box1, box3) == 0.0


def test_determine_relative_position():
    box = BoundingBox(x1=100.0, y1=100.0, x2=200.0, y2=200.0)

    assert is_point_inside_box((150.0, 150.0), box) is True
    assert determine_relative_position((150.0, 150.0), box) == "INSIDE"

    # Above
    assert determine_relative_position((150.0, 50.0), box) == "ABOVE"
    # Below
    assert determine_relative_position((150.0, 250.0), box) == "BELOW"
    # Left
    assert determine_relative_position((50.0, 150.0), box) == "LEFT"
    # Right
    assert determine_relative_position((250.0, 150.0), box) == "RIGHT"


def test_compute_velocity_vector():
    p1 = (100.0, 100.0)
    p2 = (110.0, 120.0)
    dt = 0.5
    v = compute_velocity_vector(p2, p1, dt)
    assert v == (20.0, 40.0)


def test_compute_motion_correlation():
    # Co-directional vectors -> cosine = 1.0
    v1 = (30.0, 40.0)
    v2 = (60.0, 80.0)
    assert compute_motion_correlation(v1, v2) == pytest.approx(1.0)

    # Opposing vectors -> cosine = -1.0
    v3 = (-30.0, -40.0)
    assert compute_motion_correlation(v1, v3) == pytest.approx(-1.0)

    # Orthogonal vectors -> cosine = 0.0
    v4 = (-40.0, 30.0)
    assert compute_motion_correlation(v1, v4) == pytest.approx(0.0, abs=1e-2)

    # Below minimal speed -> returns 0.0
    v_slow = (1.0, 1.0)
    assert compute_motion_correlation(v1, v_slow) == 0.0


def test_compute_approach_speed():
    # Approaching: distance decreases from 0.40 to 0.30 over 0.5s -> -0.20
    speed = compute_approach_speed(0.30, 0.40, 0.5)
    assert speed == pytest.approx(-0.20)

    # Separating: distance increases from 0.30 to 0.40 over 0.5s -> +0.20
    speed2 = compute_approach_speed(0.40, 0.30, 0.5)
    assert speed2 == pytest.approx(0.20)

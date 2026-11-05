"""Unit tests for optical frame quality evaluation."""

import numpy as np
import pytest

from core.perception.quality import FrameQualityAnalyzer, QualityGrade


def test_frame_quality_analyzer():
    """Verify quality grading on synthetic test images."""
    analyzer = FrameQualityAnalyzer(min_blur_threshold=50.0, min_brightness=30.0, max_brightness=220.0)

    # 1. Blank solid black image (DARK and BLURRY)
    black_img = np.zeros((200, 200, 3), dtype=np.uint8)
    q_black = analyzer.analyze(black_img)
    assert q_black.is_acceptable is False
    assert q_black.blur_score < 5.0

    # 2. Solid white image (OVEREXPOSED)
    white_img = np.full((200, 200, 3), 255, dtype=np.uint8)
    q_white = analyzer.analyze(white_img)
    assert q_white.grade in (QualityGrade.BLURRY, QualityGrade.OVEREXPOSED)

    # 3. High contrast textured image (GOOD)
    textured = np.zeros((200, 200, 3), dtype=np.uint8)
    textured[::4, :] = 160
    textured[1::4, :] = 80
    textured[2::4, :] = 160
    textured[3::4, :] = 80
    q_tex = analyzer.analyze(textured)
    assert q_tex.blur_score > 50.0
    assert q_tex.grade == QualityGrade.GOOD
    assert q_tex.is_acceptable is True

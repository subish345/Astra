"""Frame visual quality evaluation and diagnostic metrics for ASTRA-EA.

Computes blur, illumination, contrast, and dimensions to expose evidence quality
factors to downstream assurance and uncertainty handlers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np


class QualityGrade(str, Enum):
    """Overall visual quality assessment grade."""
    GOOD = "GOOD"
    BLURRY = "BLURRY"
    DARK = "DARK"
    OVEREXPOSED = "OVEREXPOSED"
    LOW_CONTRAST = "LOW_CONTRAST"


@dataclass
class FrameQuality:
    """Quantitative frame optical quality assessment metrics."""
    grade: QualityGrade
    blur_score: float  # Variance of Laplacian (higher = sharper, < 60 = blurry)
    brightness: float  # Mean pixel luminance [0.0, 255.0]
    contrast: float    # Standard deviation of luminance
    is_acceptable: bool
    width: int
    height: int


class FrameQualityAnalyzer:
    """Evaluates optical metrics of ingested video frames."""

    def __init__(
        self,
        min_blur_threshold: float = 60.0,
        min_brightness: float = 35.0,
        max_brightness: float = 230.0,
        min_contrast: float = 20.0,
    ):
        self.min_blur_threshold = min_blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_contrast = min_contrast

    def analyze(self, image: np.ndarray) -> FrameQuality:
        """Calculate optical properties on an RGB/BGR image."""
        h, w = image.shape[:2]

        if len(image.shape) == 3 and image.shape[2] >= 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 1. Blur calculation via Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = float(laplacian.var())

        # 2. Brightness (mean) and Contrast (std dev)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        # 3. Grade determination
        if blur_score < self.min_blur_threshold:
            grade = QualityGrade.BLURRY
            acceptable = False
        elif mean_lum < self.min_brightness:
            grade = QualityGrade.DARK
            acceptable = False
        elif mean_lum > self.max_brightness:
            grade = QualityGrade.OVEREXPOSED
            acceptable = False
        elif std_lum < self.min_contrast:
            grade = QualityGrade.LOW_CONTRAST
            acceptable = True
        else:
            grade = QualityGrade.GOOD
            acceptable = True

        return FrameQuality(
            grade=grade,
            blur_score=round(blur_score, 2),
            brightness=round(mean_lum, 2),
            contrast=round(std_lum, 2),
            is_acceptable=acceptable,
            width=w,
            height=h,
        )

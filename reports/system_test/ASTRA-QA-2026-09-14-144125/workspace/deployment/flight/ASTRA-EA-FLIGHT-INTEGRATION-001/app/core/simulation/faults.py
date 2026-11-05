"""Modular Fault Injection Operators for ASTRA-EA Simulation.

Implements parameterized optical, environmental, sensor, and behavioral
degradation transforms applied to video frames and pipeline states.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


class FaultInjectors:
    """Library of deterministic and stochastic fault injection transforms."""

    @staticmethod
    def apply_low_light(img: np.ndarray, intensity: float = 0.75) -> np.ndarray:
        """Simulate severe cabin illumination drop / power-saving mode."""
        # Scale brightness while preserving basic hue channels
        factor = max(0.10, 1.0 - (intensity * 0.85))
        return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_glare(
        img: np.ndarray,
        intensity: float = 0.80,
        center: Optional[Tuple[int, int]] = None,
        radius: Optional[int] = None,
    ) -> np.ndarray:
        """Inject high-intensity specular bloom / solar glare on workstation."""
        h, w = img.shape[:2]
        cx = center[0] if center else int(w * 0.5)
        cy = center[1] if center else int(h * 0.4)
        rad = radius if radius else int(min(w, h) * (0.25 + 0.35 * intensity))

        mask = np.zeros((h, w), dtype=np.float32)
        cv2.circle(mask, (cx, cy), rad, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (rad | 1, rad | 1), 0)

        glare_img = img.astype(np.float32)
        for c in range(3):
            glare_img[:, :, c] += mask * (255.0 * intensity)

        return np.clip(glare_img, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_occlusion(
        img: np.ndarray,
        intensity: float = 0.85,
        bbox: Optional[Tuple[int, int, int, int]] = None,
    ) -> np.ndarray:
        """Simulate physical visual obstacle blocking hands or target items."""
        res = img.copy()
        h, w = img.shape[:2]
        if bbox:
            x1, y1, x2, y2 = bbox
        else:
            # Default center-right occlusion covering specimen interaction zone
            x1 = int(w * 0.35)
            y1 = int(h * 0.35)
            x2 = int(w * (0.35 + 0.30 * intensity))
            y2 = int(h * (0.35 + 0.40 * intensity))

        # Draw opaque dark obstacle
        cv2.rectangle(res, (x1, y1), (x2, y2), (30, 30, 35), -1)
        cv2.rectangle(res, (x1, y1), (x2, y2), (70, 70, 80), 2)
        return res

    @staticmethod
    def apply_lens_smudge(img: np.ndarray, intensity: float = 0.70) -> np.ndarray:
        """Simulate glove smudge or condensation film across optical lens."""
        ksize = int(15 * intensity) | 1
        blurred = cv2.GaussianBlur(img, (ksize, ksize), 0)
        # Blend blurred with original
        alpha = min(0.90, 0.40 + 0.50 * intensity)
        return cv2.addWeighted(blurred, alpha, img, 1.0 - alpha, 0)

    @staticmethod
    def apply_noise(img: np.ndarray, intensity: float = 0.50) -> np.ndarray:
        """Simulate sensor thermal noise and grain."""
        h, w, c = img.shape
        noise = np.random.normal(0, 35 * intensity, (h, w, c)).astype(np.float32)
        noisy = img.astype(np.float32) + noise
        return np.clip(noisy, 0, 255).astype(np.uint8)

    @staticmethod
    def apply_motion_blur(img: np.ndarray, intensity: float = 0.60, angle: float = 0.0) -> np.ndarray:
        """Simulate camera or operator rapid motion blur."""
        size = max(3, int(25 * intensity))
        kernel = np.zeros((size, size))
        kernel[int((size - 1) / 2), :] = np.ones(size)
        kernel = kernel / size

        # Rotate kernel if angle specified
        if angle != 0.0:
            M = cv2.getRotationMatrix2D((size / 2, size / 2), angle, 1.0)
            kernel = cv2.warpAffine(kernel, M, (size, size))

        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def apply_black_frame(shape: Tuple[int, int, int] = (480, 640, 3)) -> np.ndarray:
        """Simulate sudden camera hardware disconnect or total blackout."""
        return np.zeros(shape, dtype=np.uint8)

    @staticmethod
    def apply_wrong_object_swap(img: np.ndarray, intensity: float = 1.0) -> np.ndarray:
        """
        Photometrically swap Red Specimen colors to Yellow.
        Simulates astronaut presenting or interacting with the wrong specimen box.
        """
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Red mask in HSV
        lower_red1 = np.array([0, 100, 70])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 70])
        upper_red2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Shift hue to Yellow (approx Hue 25-30)
        hsv_mod = hsv.copy()
        hsv_mod[:, :, 0][red_mask > 0] = 28
        hsv_mod[:, :, 1][red_mask > 0] = 230

        return cv2.cvtColor(hsv_mod, cv2.COLOR_HSV2BGR)

    @staticmethod
    def apply_latency_spike(intensity: float = 0.80, max_delay_ms: float = 250.0) -> float:
        """Simulate inference computation delay due to thermal throttling."""
        delay_sec = (intensity * max_delay_ms) / 1000.0
        time.sleep(delay_sec)
        return delay_sec

"""Unit tests for Fault Injection Operators (D8.03, D8.05, D8.06, D8.07)."""

from __future__ import annotations

import numpy as np
import pytest

from core.simulation.faults import FaultInjectors
from core.simulation.scenario import FaultTrigger, FaultType


@pytest.fixture
def sample_image() -> np.ndarray:
    """Create a standardized test image with non-zero pixel values."""
    img = np.full((120, 160, 3), 128, dtype=np.uint8)
    # Add high-contrast red feature (BGR: B=30, G=30, R=220)
    img[40:80, 50:110] = [30, 30, 220]
    return img


def test_fault_trigger_active_window():
    """Verify FaultTrigger.is_active boundary conditions."""
    trigger = FaultTrigger(
        fault_type=FaultType.LOW_LIGHT,
        start_time=2.0,
        duration_sec=3.0,
        intensity=0.7,
    )
    assert not trigger.is_active(1.99)
    assert trigger.is_active(2.00)
    assert trigger.is_active(3.50)
    assert trigger.is_active(4.99)
    assert not trigger.is_active(5.00)
    assert not trigger.is_active(5.01)


def test_apply_low_light(sample_image):
    """Verify low light decreases mean luminance without altering dimensions."""
    original_mean = np.mean(sample_image)
    dark = FaultInjectors.apply_low_light(sample_image, intensity=0.75)

    assert dark.shape == sample_image.shape
    assert dark.dtype == np.uint8
    assert np.mean(dark) < original_mean
    assert np.all(dark <= sample_image)


def test_apply_glare(sample_image):
    """Verify glare increases luminance and blooms pixels."""
    original_mean = np.mean(sample_image)
    glare = FaultInjectors.apply_glare(sample_image, intensity=0.80)

    assert glare.shape == sample_image.shape
    assert glare.dtype == np.uint8
    assert np.mean(glare) > original_mean
    # Center should have saturated pixels
    h, w = sample_image.shape[:2]
    center_val = glare[h // 2, w // 2]
    assert np.any(center_val >= 200)


def test_apply_occlusion(sample_image):
    """Verify occlusion places a low-luminance mask."""
    occluded = FaultInjectors.apply_occlusion(sample_image, intensity=0.60)

    assert occluded.shape == sample_image.shape
    assert occluded.dtype == np.uint8
    # Center rectangle should be dark/neutral
    h, w = sample_image.shape[:2]
    center_val = occluded[h // 2, w // 2]
    assert np.all(center_val <= 40)


def test_apply_lens_smudge(sample_image):
    """Verify lens smudge blurs localized region."""
    smudged = FaultInjectors.apply_lens_smudge(sample_image, intensity=0.80)

    assert smudged.shape == sample_image.shape
    assert smudged.dtype == np.uint8
    # High-frequency difference should be non-zero
    diff = np.abs(smudged.astype(np.int16) - sample_image.astype(np.int16))
    assert np.sum(diff) > 0


def test_apply_noise(sample_image):
    """Verify Gaussian noise injection alters pixel distribution."""
    noisy = FaultInjectors.apply_noise(sample_image, intensity=0.50)

    assert noisy.shape == sample_image.shape
    assert noisy.dtype == np.uint8
    assert not np.array_equal(noisy, sample_image)


def test_apply_motion_blur(sample_image):
    """Verify linear motion blur is applied without shape distortion."""
    blurred = FaultInjectors.apply_motion_blur(sample_image, intensity=0.75)

    assert blurred.shape == sample_image.shape
    assert blurred.dtype == np.uint8
    assert not np.array_equal(blurred, sample_image)


def test_apply_black_frame():
    """Verify black frame produces an all-zero image."""
    shape = (100, 100, 3)
    black = FaultInjectors.apply_black_frame(shape)

    assert black.shape == shape
    assert black.dtype == np.uint8
    assert np.all(black == 0)


def test_apply_wrong_object_swap(sample_image):
    """Verify wrong object color swap modifies target pixel region."""
    swapped = FaultInjectors.apply_wrong_object_swap(sample_image, intensity=1.0)

    assert swapped.shape == sample_image.shape
    assert swapped.dtype == np.uint8
    # Object region should have shifted colors
    assert not np.array_equal(swapped, sample_image)


def test_apply_latency_spike():
    """Verify latency spike runs without throwing exceptions."""
    import time
    t0 = time.time()
    FaultInjectors.apply_latency_spike(intensity=0.1)
    t_elapsed = time.time() - t0
    assert t_elapsed >= 0.01

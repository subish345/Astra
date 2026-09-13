"""Unit tests for DeviceManager hardware inspection."""

import pytest

from core.perception.device import DeviceInfo, DeviceManager


def test_device_manager_cpu_request():
    """Verify requesting CPU explicitly resolves to CPU backend."""
    info = DeviceManager.get_device_info("cpu")
    assert info.backend == "cpu"
    assert info.is_cuda is False


def test_device_manager_auto_resolution():
    """Verify auto mode resolves to a valid backend without crashing."""
    info = DeviceManager.get_device_info("auto")
    assert info.backend in ("cuda", "cpu")
    assert isinstance(info.device_name, str)
    assert len(info.device_name) > 0

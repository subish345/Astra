"""Automated Test Suite for Flight Startup and Security Guards (Phase 18)."""

import pytest

from core.flight.runtime_mode import FlightSecurityGuard, RuntimeMode, SecurityPolicyViolation
from core.flight.startup import BootState, FlightStartupSequence
from core.platform.camera import SimulatedCameraDriver
from core.platform.platform import PlatformProfile


def test_flight_startup_sequence_nominal():
    """Verify nominal 9-stage boot sequence reaches READY state."""
    cam = SimulatedCameraDriver()
    startup = FlightStartupSequence(
        runtime_mode=RuntimeMode.FLIGHT_INTEGRATION,
        platform_profile=PlatformProfile.FLIGHT_TARGET_TBD,
        camera_driver=cam,
    )
    state = startup.execute_startup()
    assert state == BootState.READY
    assert startup.failure_reason is None
    assert len(startup.stage_timings) >= 8
    assert startup.startup_report["boot_state"] == "READY"
    assert startup.startup_report["total_startup_duration_ms"] > 0


def test_flight_startup_camera_failure():
    """Verify boot failure state when camera fails to initialize (Section 11)."""
    cam = SimulatedCameraDriver()
    cam.inject_failure(True)
    startup = FlightStartupSequence(
        runtime_mode=RuntimeMode.FLIGHT_INTEGRATION,
        platform_profile=PlatformProfile.FLIGHT_TARGET_TBD,
        camera_driver=cam,
    )
    # Force camera init to fail
    cam.initialize = lambda: False
    state = startup.execute_startup()
    assert state == BootState.CAMERA_FAILURE
    assert startup.failure_reason is not None


def test_flight_security_guard():
    """Verify flight mode blocks developer controls and synthetic data injection (Section 9 & 39)."""
    guard = FlightSecurityGuard(mode=RuntimeMode.FLIGHT_INTEGRATION)

    with pytest.raises(SecurityPolicyViolation):
        guard.assert_debug_allowed()

    with pytest.raises(SecurityPolicyViolation):
        guard.assert_config_mutation_allowed()

    with pytest.raises(SecurityPolicyViolation):
        guard.assert_synthetic_injection_allowed()

    with pytest.raises(SecurityPolicyViolation):
        guard.assert_model_swapping_allowed()

    # In development mode, these operations are permitted
    dev_guard = FlightSecurityGuard(mode=RuntimeMode.DEVELOPMENT)
    dev_guard.assert_debug_allowed()
    dev_guard.assert_config_mutation_allowed()
    dev_guard.assert_synthetic_injection_allowed()
    dev_guard.assert_model_swapping_allowed()

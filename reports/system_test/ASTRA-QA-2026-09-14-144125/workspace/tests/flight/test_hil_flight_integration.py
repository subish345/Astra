"""Automated Test Suite for HIL Flight Integration Matrix (Phase 18)."""

import json
from pathlib import Path
import pytest

from core.hil.flight_runner import HILFlightIntegrationRunner
from core.hil.hil_platform import HILPlatform, HILPlatformConfig


def test_hil_platform_swappable_drivers():
    """Verify HILPlatform correctly provides swappable simulated drivers."""
    platform = HILPlatform(HILPlatformConfig(simulated_camera=True, simulated_clock=True))
    assert platform.initialize() is True

    # Check camera frame
    ret = platform.camera.read_frame()
    assert ret is not None
    frame, ts = ret
    assert frame.shape == (720, 1280, 3)

    # Fault injection
    platform.inject_camera_fault(True)
    assert platform.camera.read_frame() is None

    platform.inject_telemetry_disconnect(True)
    assert platform.telemetry.is_connected is False

    platform.shutdown()


def test_hil_flight_integration_all_scenarios(tmp_path):
    """Verify all 12 operational scenarios in the formal HIL test matrix (Section 70)."""
    runner = HILFlightIntegrationRunner()
    runner.reports_dir = tmp_path / "hil_reports"
    runner.reports_dir.mkdir(parents=True, exist_ok=True)

    summary = runner.run_all()
    assert summary["overall_status"] == "PASS"
    assert summary["total_scenarios"] == 12
    assert summary["passed"] == 12
    assert summary["failed"] == 0

    # Verify reports generated on disk
    json_rep = runner.reports_dir / "hil_flight_integration_report.json"
    html_rep = runner.reports_dir / "hil_flight_integration_report.html"
    assert json_rep.exists()
    assert html_rep.exists()

    with open(json_rep, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["overall_status"] == "PASS"
        assert len(data["scenarios"]) == 12

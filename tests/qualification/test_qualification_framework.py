"""Automated Pytest Suite for Phase 15 Qualification Readiness Subsystem."""

import json
from pathlib import Path
import pytest

from core.integration.bus import (
    PowerState,
    ThermalState,
    TimeSourceInterface,
    VehicleBusAdapter,
    VehicleTelemetryPacket,
)
from core.qualification.engine import QualificationEngine


def test_vehicle_data_bus_adapter():
    """Verify VehicleBusAdapter registers commands and transmits telemetry."""
    bus = VehicleBusAdapter("TEST_BUS")
    assert bus.bus_id == "TEST_BUS"
    assert bus.power_state == PowerState.POWER_GOOD
    assert bus.thermal_state == ThermalState.THERMAL_NORMAL

    # Register command
    bus.register_command_handler("PING", lambda p: {"status": "PONG", "echo": p.get("data")})
    res = bus.dispatch_command("PING", {"data": 123})
    assert res["status"] == "PONG"
    assert res["echo"] == 123

    # State update
    bus.update_power_state(PowerState.POWER_DEGRADED)
    assert bus.power_state == PowerState.POWER_DEGRADED

    bus.update_thermal_state(ThermalState.THERMAL_WARNING)
    assert bus.thermal_state == ThermalState.THERMAL_WARNING


def test_time_source_interface():
    """Verify TimeSourceInterface maintains monotonic and UTC time."""
    ts = TimeSourceInterface()
    iso = ts.get_scet_timestamp_iso()
    dur = ts.get_monotonic_duration_sec()
    assert "T" in iso and "Z" in iso
    assert dur >= 0.0


def test_qualification_engine_reports():
    """Verify QualificationEngine audits requirements and produces reports."""
    engine = QualificationEngine()
    req_data = engine.audit_requirements()
    assert req_data["total_requirements"] > 25
    assert req_data["verified_count"] > 20
    assert req_data["planned_count"] >= 3

    reports = engine.generate_all_reports()
    assert reports["readiness_verdict"] == "READY"

    # Check generated files
    q_dir = Path("reports/qualification")
    assert (q_dir / "readiness.json").exists()
    assert (q_dir / "readiness.html").exists()
    assert (q_dir / "requirements.html").exists()
    assert (q_dir / "verification-matrix.html").exists()
    assert (q_dir / "fmea.html").exists()
    assert (q_dir / "resource-budget.html").exists()
    assert (q_dir / "interface-control.html").exists()

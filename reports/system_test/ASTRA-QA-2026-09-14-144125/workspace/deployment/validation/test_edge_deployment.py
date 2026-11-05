"""Automated Pytest Suite for Phase 14 Edge Deployment Package."""

import os
from pathlib import Path
import pytest

from core.hardware.edge_diagnostics import get_edge_hardware_profile
from core.hardware.physical_runner import PhysicalExperimentRunner
from core.hardware.hil_runner import HILRunner


def test_edge_hardware_profile_structure():
    """Verify hardware profile contains all required architecture keys."""
    prof = get_edge_hardware_profile()
    assert "platform" in prof
    assert "cpu_model" in prof
    assert "ram_total_mb" in prof
    assert "disk_free_gb" in prof
    assert "inference_runtime" in prof
    assert "model_name" in prof
    assert prof["ram_total_mb"] > 0


def test_physical_runner_execution():
    """Verify PhysicalExperimentRunner executes without error."""
    runner = PhysicalExperimentRunner(profile_id="VIEW_LEFT", duration_sec=1)
    summary = runner.run_physical_validation()
    assert summary["overall_status"] == "PASS"
    assert summary["profile_id"] == "VIEW_LEFT"
    assert Path("reports/physical/physical_validation.json").exists()
    assert Path("reports/physical/physical_validation.html").exists()


def test_hil_runner_wrong_object():
    """Verify HIL runner evaluates wrong-object scenario."""
    hil = HILRunner(scenario="WRONG_OBJECT")
    summary = hil.run_hil_scenario()
    assert summary["status"] == "PASS"
    assert summary["scenario"] == "WRONG_OBJECT"
    assert Path("reports/hil/hil_validation.json").exists()
    assert Path("reports/hil/simulation_vs_physical.html").exists()
    assert Path("reports/hil/hardware_matrix.html").exists()

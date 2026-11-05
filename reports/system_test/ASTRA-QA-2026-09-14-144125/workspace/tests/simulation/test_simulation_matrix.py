"""Tests for Batch Simulation Matrix Runner (D8.09, D8.11)."""

from __future__ import annotations

from pathlib import Path
import pytest

from core.simulation.matrix import SimulationMatrixRunner
from core.simulation.scenario import SimulationScenario


def test_simulation_matrix_runner(tmp_path: Path):
    """Verify batch matrix execution across multiple scenario types."""
    runner = SimulationMatrixRunner(
        config_path="configs/system.yaml",
        reports_dir=str(tmp_path),
    )

    scen_nominal = SimulationScenario.load_yaml("configs/simulations/nominal_mission.yaml")
    scen_wrong = SimulationScenario.load_yaml("configs/simulations/wrong_object_fault.yaml")

    report = runner.run_matrix(
        scenarios=[scen_nominal, scen_wrong],
        matrix_name="Test Sub-Matrix",
        max_frames_per_scenario=60,
    )

    assert report["total_scenarios"] == 2
    assert report["passed_scenarios"] == 2
    assert report["pass_rate"] == 100.0
    assert report["average_resilience_score"] >= 75.0
    assert report["total_crashes"] == 0

    assert (tmp_path / "simulation_matrix_report.json").exists()
    assert (tmp_path / "simulation_matrix_report.html").exists()


def test_simulation_matrix_config_loading(tmp_path: Path):
    """Verify runner loads matrix configuration file."""
    runner = SimulationMatrixRunner(
        config_path="configs/system.yaml",
        reports_dir=str(tmp_path),
    )

    report = runner.run_matrix_config(
        config_path="configs/simulations/full_matrix.yaml",
        max_frames=120,
    )

    assert report["total_scenarios"] == 6
    assert report["passed_scenarios"] == 6
    assert report["pass_rate"] == 100.0

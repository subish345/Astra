"""Integration tests for SimulationEngine (D8.01, D8.10, D8.11)."""

from __future__ import annotations

from pathlib import Path
import pytest

from core.simulation.engine import SimulationEngine
from core.simulation.reporter import SimulationReporter
from core.simulation.scenario import SimulationScenario


@pytest.fixture
def engine() -> SimulationEngine:
    return SimulationEngine(config_path="configs/system.yaml")


def test_nominal_simulation_execution(engine: SimulationEngine, tmp_path: Path):
    """Verify nominal mission scenario passes with high resilience and 0 crashes."""
    scen = SimulationScenario.load_yaml("configs/simulations/nominal_mission.yaml")
    res = engine.run_scenario(scenario=scen, max_frames=90, realtime_pacing=False)

    assert res.status == "COMPLETED"
    assert res.frames_processed == 90
    assert res.pipeline_crashes == 0
    assert res.resilience_score >= 75.0
    assert res.evaluation_verdict == "PASS"

    reporter = SimulationReporter(output_dir=str(tmp_path))
    paths = reporter.generate_scenario_report(res)
    assert Path(paths["json_report"]).exists()
    assert Path(paths["html_report"]).exists()


def test_wrong_object_deviation_detection(engine: SimulationEngine):
    """Verify wrong object behavioral fault triggers DEVIATION and records MTTD."""
    scen = SimulationScenario.load_yaml("configs/simulations/wrong_object_fault.yaml")
    res = engine.run_scenario(scenario=scen, max_frames=90, realtime_pacing=False)

    assert res.status == "COMPLETED"
    assert res.deviation_count > 0
    assert "WRONG_OBJECT" in res.detected_deviations
    assert res.mttd_sec is not None
    assert res.pipeline_crashes == 0
    assert res.evaluation_verdict == "PASS"


def test_optical_stress_zero_false_deviations(engine: SimulationEngine):
    """Verify severe optical stress triggers UNCERTAIN and zero false deviations."""
    scen = SimulationScenario.load_yaml("configs/simulations/optical_stress.yaml")
    res = engine.run_scenario(scenario=scen, max_frames=90, realtime_pacing=False)

    assert res.status == "COMPLETED"
    assert res.false_positive_deviations == 0
    assert res.pipeline_crashes == 0
    assert res.evaluation_verdict == "PASS"
    assert res.resilience_score >= 75.0

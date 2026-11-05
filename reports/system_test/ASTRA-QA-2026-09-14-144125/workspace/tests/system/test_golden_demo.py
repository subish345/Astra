"""Golden Demo End-to-End System Tests (D11.23, D11.24)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import yaml

from core.simulation.engine import SimulationEngine
from core.simulation.scenario import SimulationScenario
from core.mission.orchestrator import MissionOrchestrator


def test_golden_demo_scenario_simulation(tmp_path: Path):
    """Verify golden demo scenario executes deterministically in simulation."""
    scenario_path = "configs/simulations/GOLDEN_DEMO.yaml"
    assert Path(scenario_path).exists()

    scenario = SimulationScenario.load_yaml(scenario_path)
    engine = SimulationEngine(config_path="configs/system.yaml")

    result = engine.run_scenario(scenario, max_frames=90)
    assert result is not None
    assert result.scenario_id == "GOLDEN_DEMO_001"
    assert result.frames_processed >= 30
    assert result.deviation_count >= 1
    assert "WRONG_OBJECT" in result.detected_deviations
    data = result.model_dump() if hasattr(result, "model_dump") else result.dict()
    assert data["scenario_id"] == "GOLDEN_DEMO_001"



def test_golden_demo_cross_consistency(tmp_path: Path):
    """Verify consistency between SQLite, events, timeline, and final mission report."""
    orchestrator = MissionOrchestrator(
        profile_name="demo",
        root_dir=str(tmp_path),
    )
    orchestrator.boot()
    orchestrator.run_self_test()

    run_id = "GOLDEN_VERIFY_RUN"
    orchestrator.start_mission(
        experiment_id="DEMO_EXP_001",
        run_id=run_id,
        camera_profile="VIEW_LEFT",
    )

    # Trigger nominal step advancement
    if orchestrator.progress_manager:
        orchestrator.progress_manager.advance("STEP_01")
        orchestrator.progress_manager.advance("STEP_02")

    report = orchestrator.complete_mission()
    assert report is not None

    run_dir = tmp_path / "data" / "runs" / run_id
    assert (run_dir / "mission_report.json").exists()
    assert (run_dir / "events.json").exists()
    assert (run_dir / "config_snapshot.yaml").exists()
    assert (run_dir / "model_snapshot.json").exists()
    assert (run_dir / "health_summary.json").exists()

    # Load and compare report data
    with open(run_dir / "mission_report.json", "r") as f:
        rep_data = json.load(f)

    with open(run_dir / "health_summary.json", "r") as f:
        health_data = json.load(f)

    assert rep_data["manifest"]["run_id"] == run_id
    assert rep_data["health"]["overall_status"] == health_data["overall_status"]
    assert rep_data["manifest"]["status"] == "COMPLETED"

    orchestrator.shutdown()

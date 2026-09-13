"""Tests for Mission Rehearsal Framework and Multi-Mode Orchestrator (Phase 20, D20.02 - D20.05)."""

import json
from pathlib import Path
import pytest

from core.operations.rehearsal import (
    MissionRehearsalEngine,
    RehearsalMode,
    RehearsalRunResult,
    RehearsalSpeed,
)
from core.operations.rehearsal_scenarios import ScenarioId


def test_rehearsal_engine_init(tmp_path: Path) -> None:
    """Verify clean initialization of the rehearsal framework."""
    engine = MissionRehearsalEngine(
        scenario_name="GOLDEN_MISSION",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        operator="TEST_OPERATOR_01",
        project_root=tmp_path,
    )
    assert engine.scenario_id == ScenarioId.GOLDEN_MISSION
    assert engine.mode == RehearsalMode.SIMULATION
    assert engine.speed == RehearsalSpeed.ACCELERATED
    assert engine.operator == "TEST_OPERATOR_01"
    assert len(engine.milestones) == 10
    assert not engine.is_completed
    assert engine.current_step_index == 0


def test_rehearsal_engine_stepwise_advance(tmp_path: Path) -> None:
    """Verify STEPWISE milestone-by-milestone advancement (Section 49)."""
    engine = MissionRehearsalEngine(
        scenario_name="GOLDEN_MISSION",
        mode=RehearsalMode.STEPWISE,
        speed=RehearsalSpeed.STEPWISE,
        project_root=tmp_path,
    )

    # Step 1
    s1 = engine.advance_step()
    assert s1 is not None
    assert s1["step_index"] == 1
    assert s1["phase"] == "PREPARATION"
    assert s1["event_type"] == "PRECHECK_COMPLETED"
    assert s1["sequence_num"] == 101

    # Advance remaining steps
    for _ in range(9):
        res = engine.advance_step()
        assert res is not None

    # Reached end
    assert engine.is_completed
    assert engine.advance_step() is None
    assert len(engine.rehearsal_log) == 10


def test_rehearsal_engine_run_all_and_artifacts(tmp_path: Path) -> None:
    """Verify automated execution, callbacks, and artifact generation (Section 42)."""
    engine = MissionRehearsalEngine(
        scenario_name="GOLDEN_MISSION",
        mode=RehearsalMode.FULL_REAL,
        speed=RehearsalSpeed.ACCELERATED,
        operator="ASTRONAUT_ALPHA",
        project_root=tmp_path,
    )

    callbacks_received = []
    result = engine.run_all(event_callback=lambda evt: callbacks_received.append(evt))

    assert result.status == "PASS"
    assert result.data_consistency == "CONSISTENT"
    assert result.executed_steps == 10
    assert result.deviations_count == 1
    assert result.recoveries_count == 1
    assert result.false_verifications == 0
    assert result.false_deviations == 0
    assert len(callbacks_received) == 10

    # Verify bundle contents per Section 42
    bundle_path = Path(result.artifacts_dir)
    assert bundle_path.exists()
    assert (bundle_path / "scorecard.json").is_file()
    assert (bundle_path / "events.json").is_file()
    assert (bundle_path / "timeline.json").is_file()
    assert (bundle_path / "health.json").is_file()
    assert (bundle_path / "evidence_manifest.json").is_file()
    assert (bundle_path / "configuration_snapshot.yaml").is_file()
    assert (bundle_path / "rehearsal_notes.md").is_file()
    assert (bundle_path / "mission_report.html").is_file()

    # Verify event stream monotonically increases
    with open(bundle_path / "events.json", "r", encoding="utf-8") as f:
        events_data = json.load(f)
    seqs = [e["sequence_num"] for e in events_data["events"]]
    assert seqs == sorted(seqs)
    assert len(seqs) == len(set(seqs))

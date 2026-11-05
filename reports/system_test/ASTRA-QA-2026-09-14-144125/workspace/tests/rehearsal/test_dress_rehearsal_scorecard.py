"""Tests for Dress Rehearsal and Rehearsal Scorecard Generation (Phase 20, D20.18 - D20.20)."""

import json
from pathlib import Path
import pytest

from core.operations.rehearsal import (
    MissionRehearsalEngine,
    RehearsalMode,
    RehearsalSpeed,
)
from core.operations.scorecard import RehearsalScorecardGenerator


def test_dress_rehearsal_execution_and_report(tmp_path: Path) -> None:
    """D20.18 & D20.20: Full-length Dress Rehearsal under FULL_REAL mode with report."""
    eng = MissionRehearsalEngine(
        scenario_name="DRESS_REHEARSAL",
        mode=RehearsalMode.FULL_REAL,
        speed=RehearsalSpeed.ACCELERATED,
        operator="COMMANDER_ASTRO_1",
        project_root=tmp_path,
    )
    result = eng.run_all()
    assert result.status == "PASS"
    assert result.data_consistency == "CONSISTENT"
    assert result.deviations_count == 1
    assert result.recoveries_count == 1
    assert result.false_verifications == 0

    # Ensure zero developer interventions
    rev = next(e for e in eng.rehearsal_log if e["event_type"] == "GROUND_REVIEW_COMPLETED")
    assert rev["payload"]["developer_interventions"] == 0

    # Test Dress Rehearsal HTML Report generator
    gen = RehearsalScorecardGenerator(tmp_path)
    report_file = gen.generate_dress_rehearsal_report(result)
    assert report_file.is_file()
    content = report_file.read_text(encoding="utf-8")
    assert "ASTRA-EA Full Mission Dress Rehearsal Report" in content
    assert "ZERO developer interventions" in content
    assert result.run_id in content


def test_scorecard_generator_multi_runs(tmp_path: Path) -> None:
    """D20.19: Multi-run scorecard compilation and HTML dashboard rendering."""
    scenarios = ["REH_01_DEVIATION", "REH_02_CLEAN", "REH_03_UNCERTAINTY"]
    results = []
    for sc in scenarios:
        eng = MissionRehearsalEngine(
            scenario_name=sc,
            mode=RehearsalMode.SIMULATION,
            speed=RehearsalSpeed.ACCELERATED,
            project_root=tmp_path,
        )
        results.append(eng.run_all())

    gen = RehearsalScorecardGenerator(tmp_path)
    scorecard = gen.generate_scorecard(results)

    assert scorecard.overall_verdict == "PASS"
    assert scorecard.total_rehearsals_evaluated == 3
    assert scorecard.successful_rehearsals == 3
    assert scorecard.failed_rehearsals == 0
    assert scorecard.step_verification_rate_pct == 100.0
    assert scorecard.false_verifications_count == 0
    assert scorecard.false_deviations_count == 0
    assert scorecard.data_consistency_rate_pct == 100.0
    assert scorecard.avg_step_latency_ms > 0

    # Check generated files
    sc_json = tmp_path / "reports" / "rehearsal" / "scorecard.json"
    sc_html = tmp_path / "reports" / "rehearsal" / "scorecard.html"
    assert sc_json.is_file()
    assert sc_html.is_file()

    with open(sc_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["overall_verdict"] == "PASS"
    assert len(data["run_summaries"]) == 3

    html_text = sc_html.read_text(encoding="utf-8")
    assert "ASTRA-EA Operational Rehearsal Scorecard" in html_text
    assert "SCORECARD: PASS" in html_text


def test_data_consistency_check(tmp_path: Path) -> None:
    """Section 41: Strict relational consistency verification."""
    eng = MissionRehearsalEngine(
        scenario_name="GOLDEN_MISSION",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )
    res = eng.run_all()
    assert eng._verify_data_consistency() == "CONSISTENT"

    # Simulate sequence inversion anomaly
    eng.rehearsal_log[0]["sequence_num"] = 999
    assert eng._verify_data_consistency() == "INCONSISTENT_SEQUENCE"

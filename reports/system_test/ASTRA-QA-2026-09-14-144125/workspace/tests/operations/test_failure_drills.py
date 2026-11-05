"""Automated Tests for the 7 Operational Failure Drills (Phase 19, Section 51, 52, D19.19)."""

import pytest

from core.operations.training import DrillType, OperatorTrainingEngine


def test_individual_failure_drills():
    """Verify execution and quantitative scoring for all 7 failure drills (Section 51, 52)."""
    engine = OperatorTrainingEngine()

    for drill in DrillType:
        record = engine.run_drill(drill=drill, operator="Astronaut_Candidate_01")
        assert record.drill_id == drill.value
        assert record.operator == "Astronaut_Candidate_01"
        assert record.detection_time_ms > 0.0
        assert record.response_time_ms > 0.0
        assert record.recovery_time_ms > 0.0
        assert record.verdict in ("PASS", "FAIL")
        assert record.final_state in ("RESOLVED", "DEGRADED")


def test_composite_drill_battery():
    """Verify full suite drill execution and composite score calculation."""
    engine = OperatorTrainingEngine()
    summary = engine.run_all_drills(operator="Ground_Controller_02")

    assert summary["operator"] == "Ground_Controller_02"
    assert summary["total_drills"] == 7
    assert summary["passed"] == 7
    assert summary["failed"] == 0
    assert summary["overall_status"] == "PASS"

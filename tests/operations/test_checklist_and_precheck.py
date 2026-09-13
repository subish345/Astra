"""Automated Tests for Operational Checklists and Precheck Runner (Phase 19, D19.05, D19.16)."""

import pytest

from core.operations.checklist import ChecklistEngine, ChecklistItem, ChecklistItemStatus
from core.operations.precheck import PreMissionRunner


def test_checklist_lifecycle_and_signing():
    """Verify checklist items signing, completion status, and pass criteria."""
    cl = ChecklistEngine.create_pre_mission_checklist()
    assert cl.checklist_id == "PRE_MISSION"
    assert len(cl.items) >= 8
    assert cl.is_complete() is False

    # Sign all items
    for item in cl.items:
        item.sign(
            status=ChecklistItemStatus.PASS,
            operator="Astronaut_01",
            notes="Physical inspection verified",
        )
        assert item.status == ChecklistItemStatus.PASS
        assert item.timestamp_utc is not None
        assert item.operator == "Astronaut_01"

    assert cl.is_complete() is True
    assert cl.is_passing() is True


def test_checklist_critical_failure():
    """Verify critical item failure blocks checklist passing verdict."""
    cl = ChecklistEngine.create_pre_mission_checklist()
    crit_item = cl.items[0]
    assert crit_item.critical is True

    crit_item.sign(status=ChecklistItemStatus.FAIL, operator="Engineer_01")
    assert cl.is_passing() is False


def test_pre_mission_runner_execution():
    """Verify PreMissionRunner runs comprehensive checks across all 9 subsystems."""
    runner = PreMissionRunner()
    res = runner.run_all_checks()

    assert "overall_status" in res
    assert res["overall_status"] in ("READY", "DEGRADED", "BLOCKED")
    assert len(res["checks"]) == 9
    assert res["total_duration_ms"] > 0.0

    subsystems = [c["subsystem"] for c in res["checks"]]
    expected = ["Hardware", "Camera", "Model", "Procedure", "Storage", "Clock", "Recording", "Ground Link", "Health"]
    for exp in expected:
        assert exp in subsystems

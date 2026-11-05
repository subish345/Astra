"""Automated Tests for Mission Phases and Timeline Timekeeping (Phase 19, D19.02, D19.06)."""

import pytest

from core.operations.phases import MissionPhase, MissionPhaseManager
from core.operations.timeline import MissionTimeline


def test_mission_phase_transitions():
    """Verify state machine transitions along the nominal and deviation path."""
    pm = MissionPhaseManager(initial_phase=MissionPhase.PREPARATION)
    assert pm.current_phase == MissionPhase.PREPARATION

    # Nominal transition: PREP -> INIT -> READY -> EXPERIMENT
    ok, msg = pm.transition_to(MissionPhase.INITIALIZATION)
    assert ok is True
    ok, msg = pm.transition_to(MissionPhase.READY)
    assert ok is True
    ok, msg = pm.transition_to(MissionPhase.EXPERIMENT)
    assert ok is True

    # Deviation transition: EXPERIMENT -> ANOMALY -> RECOVERY -> EXPERIMENT
    ok, msg = pm.transition_to(MissionPhase.ANOMALY)
    assert ok is True
    ok, msg = pm.transition_to(MissionPhase.RECOVERY)
    assert ok is True
    ok, msg = pm.transition_to(MissionPhase.EXPERIMENT)
    assert ok is True

    # Completion transition: EXPERIMENT -> COMPLETION -> POST_MISSION
    ok, msg = pm.transition_to(MissionPhase.COMPLETION)
    assert ok is True
    ok, msg = pm.transition_to(MissionPhase.POST_MISSION)
    assert ok is True


def test_invalid_phase_transitions_blocked():
    """Verify invalid jumps across phases are rejected."""
    pm = MissionPhaseManager(initial_phase=MissionPhase.PREPARATION)

    # Cannot jump directly from PREPARATION to EXPERIMENT or COMPLETION
    ok, msg = pm.transition_to(MissionPhase.EXPERIMENT)
    assert ok is False
    assert "Invalid phase transition" in msg

    ok, msg = pm.transition_to(MissionPhase.COMPLETION)
    assert ok is False


def test_mission_timeline_and_timestamps():
    """Verify timeline milestone recording and dual clock mappings."""
    timeline = MissionTimeline(mission_id="TEST_EXP", run_id="TEST_RUN")
    timeline.start_timeline()

    m1 = timeline.record_milestone(
        milestone_type="STEP_TRANSITION",
        title="Step 1 Verified",
        details="Approach verified",
        severity="INFO",
    )
    assert m1.sequence_num == 2
    assert m1.onboard_met_seconds >= 0.0
    assert m1.onboard_timestamp_utc is not None
    assert m1.ground_receipt_timestamp_utc is not None

    d = timeline.to_dict()
    assert d["mission_id"] == "TEST_EXP"
    assert len(d["milestones"]) == 2

# ==============================================================================
# ASTRA-EA Closed-Loop Recovery Manager Unit Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Unit tests for ClosedLoopRecoveryManager state machine."""

import pytest
from core.activity.types import ActivityObservation, TemporalWindow
from core.assistance.recovery import ClosedLoopRecoveryManager, RecoveryContext, RecoveryState
from core.assurance.types import AssuranceDecision, DecisionType
from core.common.config import get_project_root
from core.evidence.types import EvidenceBundle
from core.mission.events import DeviationReason
from core.procedure.validator import load_procedure_file


@pytest.fixture
def demo_procedure():
    root = get_project_root()
    return load_procedure_file(root / "configs" / "experiments" / "demo.yaml")


@pytest.fixture
def recovery_mgr():
    return ClosedLoopRecoveryManager()


def test_recovery_state_transitions(demo_procedure, recovery_mgr):
    step = demo_procedure.steps[1]
    states_visited = []

    def on_state(state, ctx):
        states_visited.append(state)

    recovery_mgr.add_state_listener(on_state)

    decision = AssuranceDecision(
        experiment_id=demo_procedure.id,
        step_id=step.id,
        sequence=step.sequence,
        decision=DecisionType.DEVIATION,
        confidence=0.90,
        deviation_reason=DeviationReason.WRONG_OBJECT,
        reason="Wrong object manipulated",
    )

    messages = recovery_mgr.handle_decision(decision, step)
    assert len(messages) >= 2
    assert RecoveryState.DETECTED in states_visited
    assert RecoveryState.EXPLAINING in states_visited
    assert RecoveryState.RECOMMENDING in states_visited
    assert RecoveryState.OBSERVING in states_visited
    assert recovery_mgr.current_state == RecoveryState.OBSERVING

    ctx = recovery_mgr.active_context
    assert ctx is not None
    assert ctx.step_id == step.id
    assert ctx.deviation_reason == DeviationReason.WRONG_OBJECT
    assert ctx.to_dict()["state"] == "OBSERVING"

    # Reset
    recovery_mgr.reset()
    assert recovery_mgr.current_state == RecoveryState.IDLE
    assert recovery_mgr.active_context is None


def test_recovery_observation_and_verification(demo_procedure, recovery_mgr):
    step = demo_procedure.steps[1]
    decision = AssuranceDecision(
        experiment_id=demo_procedure.id,
        step_id=step.id,
        sequence=step.sequence,
        decision=DecisionType.DEVIATION,
        confidence=0.90,
        deviation_reason=DeviationReason.WRONG_OBJECT,
        reason="Wrong object manipulated",
    )
    recovery_mgr.handle_decision(decision, step)

    # Astronaut releases the object
    act = ActivityObservation(
        activity_name="RELEASE",
        actor="astronaut",
        target_object_id="YELLOW_BOX",
        confidence=0.90,
        window=TemporalWindow(start_time=1.0, end_time=2.0),
    )
    bundle = EvidenceBundle(bundle_id="BND_REC", required_satisfied=False)

    recovered, msg = recovery_mgr.observe_corrective_action(act, bundle, step)
    assert recovered is True
    assert msg is not None
    assert recovery_mgr.current_state == RecoveryState.RECOVERY_VERIFIED

    recovery_mgr.complete_recovery()
    assert recovery_mgr.current_state == RecoveryState.IDLE

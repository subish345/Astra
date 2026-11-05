"""Unit tests for ProcedureProgressManager (D4.04)."""

import pytest

from core.activity.types import ActivityObservation, TemporalWindow
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.procedure.progress import ProcedureProgressManager
from core.procedure.schema import (
    ExperimentDefinition,
    ExperimentMetadata,
    ExperimentObject,
    ExperimentStep,
)
from core.procedure.types import ProcedureProgressEvent, ProcedureStatus


@pytest.fixture
def two_step_procedure():
    meta = ExperimentMetadata(id="TWO_STEP", name="Two Step Exp", version="1.0.0")
    steps = [
        ExperimentStep(
            id="STEP_01",
            sequence=1,
            name="First Step",
            expected_objects=["MAIN_BOX"],
            expected_actions=["APPROACH"],
            required_evidence=["OBJECT_DETECTED"],
            min_duration_seconds=1.0,
            transitions=["STEP_02"],
        ),
        ExperimentStep(
            id="STEP_02",
            sequence=2,
            name="Second Step",
            expected_objects=["RED_BOX"],
            expected_actions=["GRASP"],
            required_evidence=["OBJECT_DETECTED"],
            min_duration_seconds=1.0,
            transitions=[],
        ),
    ]
    return ExperimentDefinition(experiment=meta, steps=steps)


def test_initial_state(two_step_procedure):
    mgr = ProcedureProgressManager(procedure=two_step_procedure)
    state = mgr.get_state()
    assert state.current_step == "STEP_01"
    assert state.previous_step is None
    assert len(state.completed_steps) == 0
    assert state.procedure_status == ProcedureStatus.READY


def test_step_verification_and_advancement(two_step_procedure):
    emitted_events = []

    def callback(ev, payload):
        emitted_events.append((ev, payload))

    mgr = ProcedureProgressManager(procedure=two_step_procedure, event_callback=callback)

    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    bundle = EvidenceBundle(
        step_id="STEP_01",
        evidence_score=0.90,
        required_satisfied=True,
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95))

    state = mgr.update(activity=obs, bundle=bundle, timestamp=2.5)

    assert "STEP_01" in state.completed_steps
    assert state.previous_step == "STEP_01"
    assert state.current_step == "STEP_02"
    assert state.procedure_status == ProcedureStatus.NEXT_STEP

    # Verify discrete events emitted
    event_types = [e[0] for e in emitted_events]
    assert ProcedureProgressEvent.STEP_CANDIDATE_FOUND in event_types
    assert ProcedureProgressEvent.STEP_VERIFICATION_STARTED in event_types
    assert ProcedureProgressEvent.STEP_VERIFIED in event_types
    assert ProcedureProgressEvent.PROCEDURE_ADVANCED in event_types


def test_uncertain_evidence_prevents_advancement(two_step_procedure):
    mgr = ProcedureProgressManager(procedure=two_step_procedure)
    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.90,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    # Evidence fails required check
    bundle = EvidenceBundle(
        step_id="STEP_01",
        evidence_score=0.50,
        required_satisfied=False,
        missing_required=["OBJECT_DETECTED"],
    )

    state = mgr.update(activity=obs, bundle=bundle, timestamp=2.5)

    assert "STEP_01" not in state.completed_steps
    assert state.current_step == "STEP_01"
    assert state.uncertain_step == "STEP_01"
    assert state.procedure_status == ProcedureStatus.UNCERTAIN


def test_duplicate_activity_deduplication(two_step_procedure):
    mgr = ProcedureProgressManager(procedure=two_step_procedure)

    # First verify STEP_01
    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    bundle = EvidenceBundle(step_id="STEP_01", evidence_score=0.90, required_satisfied=True)
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95))
    mgr.update(activity=obs, bundle=bundle, timestamp=2.5)

    assert mgr.current_step == "STEP_02"

    # Send identical activity for STEP_01 again
    state2 = mgr.update(activity=obs, bundle=bundle, timestamp=3.0)
    # Should remain at STEP_02; STEP_01 should not be added again
    assert state2.current_step == "STEP_02"
    assert state2.completed_steps.count("STEP_01") == 1


def test_procedure_completion(two_step_procedure):
    mgr = ProcedureProgressManager(procedure=two_step_procedure)

    # 1. Complete STEP_01
    obs1 = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    b1 = EvidenceBundle(step_id="STEP_01", evidence_score=0.90, required_satisfied=True)
    b1.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95))
    mgr.update(obs1, b1, 2.5)

    # 2. Complete STEP_02
    obs2 = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.95,
        window=TemporalWindow(start_time=3.0, end_time=4.5),
    )
    b2 = EvidenceBundle(step_id="STEP_02", evidence_score=0.92, required_satisfied=True)
    b2.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95))
    final_state = mgr.update(obs2, b2, 4.5)

    assert final_state.current_step is None
    assert final_state.procedure_status == ProcedureStatus.COMPLETED
    assert final_state.completed_steps == ["STEP_01", "STEP_02"]

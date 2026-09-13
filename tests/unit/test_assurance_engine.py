# ==============================================================================
# ASTRA-EA Tri-State Assurance Engine Unit Tests
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Unit tests for TriStateAssuranceEngine validating deterministic decision logic."""

import pytest
from core.activity.types import ActivityObservation, TemporalWindow
from core.assurance.engine import TriStateAssuranceEngine
from core.assurance.types import AssuranceDecision, DecisionType
from core.camera.profile import get_camera_profile
from core.common.config import get_project_root
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.mission.events import DeviationReason
from core.procedure.validator import load_procedure_file


@pytest.fixture
def demo_procedure():
    root = get_project_root()
    return load_procedure_file(root / "configs" / "experiments" / "demo.yaml")


@pytest.fixture
def engine():
    return TriStateAssuranceEngine()


def test_assurance_engine_verified(demo_procedure, engine):
    step_1 = demo_procedure.steps[0]
    act = ActivityObservation(
        activity_name="APPROACH_DESTINATION",
        actor="astronaut",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=1.0, end_time=3.0),
    )
    items = {
        "actor_detected": EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=True, confidence=0.95),
        "object_detected": EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95),
    }
    bundle = EvidenceBundle(bundle_id="BND_V", items=items, required_satisfied=True, evidence_score=0.95)

    decision = engine.evaluate_step(
        current_step=step_1,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )

    assert decision.is_verified
    assert not decision.is_uncertain
    assert not decision.is_deviation
    assert decision.confidence >= 0.75
    assert decision.camera_profile == "VIEW_LEFT"
    assert decision.to_dict()["decision"] == "VERIFIED"


def test_assurance_engine_timeout(demo_procedure, engine):
    step_1 = demo_procedure.steps[0]
    step_1.timeout_seconds = 10.0

    act = ActivityObservation(
        activity_name="IDLE",
        actor="astronaut",
        target_object_id="MAIN_BOX",
        confidence=0.50,
        window=TemporalWindow(start_time=0.0, end_time=1.0),
    )
    bundle = EvidenceBundle(bundle_id="BND_T", required_satisfied=False)

    decision = engine.evaluate_step(
        current_step=step_1,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_RIGHT",
        procedure=demo_procedure,
        elapsed_step_seconds=15.0,  # Exceeds 10.0s
    )

    assert decision.is_deviation
    assert decision.deviation_reason == DeviationReason.TIMEOUT
    assert "timed out" in decision.reason.lower()


def test_assurance_engine_unexpected_action(demo_procedure, engine):
    step_2 = demo_procedure.steps[1]  # Expected: GRASP
    act = ActivityObservation(
        activity_name="POUR",  # Unauthorized action primitive for this step
        actor="astronaut",
        target_object_id="RED_BOX",
        confidence=0.88,
        window=TemporalWindow(start_time=1.0, end_time=2.0),
    )
    bundle = EvidenceBundle(bundle_id="BND_UA", required_satisfied=False)

    decision = engine.evaluate_step(
        current_step=step_2,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )

    assert decision.is_deviation
    assert decision.deviation_reason == DeviationReason.UNEXPECTED_ACTION


def test_assurance_engine_incomplete_action(demo_procedure, engine):
    step_3 = demo_procedure.steps[2]  # Transfer
    act = ActivityObservation(
        activity_name="MOVE",
        actor="astronaut",
        target_object_id="RED_BOX",
        confidence=0.85,
        window=TemporalWindow(start_time=1.0, end_time=1.5),
        metadata={"abandoned": True},
    )
    bundle = EvidenceBundle(bundle_id="BND_INC", required_satisfied=False, metadata={"abandoned": True})

    decision = engine.evaluate_step(
        current_step=step_3,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_RIGHT",
        procedure=demo_procedure,
    )

    assert decision.is_deviation
    assert decision.deviation_reason == DeviationReason.INCOMPLETE_ACTION


def test_assurance_engine_uncertain_no_false_deviation(demo_procedure, engine):
    step_2 = demo_procedure.steps[1]
    act = ActivityObservation(
        activity_name="GRASP",
        actor="astronaut",
        target_object_id="RED_BOX",
        confidence=0.45,
        window=TemporalWindow(start_time=1.0, end_time=2.0),
    )
    bundle = EvidenceBundle(bundle_id="BND_UNC", required_satisfied=False, evidence_score=0.40)

    decision = engine.evaluate_step(
        current_step=step_2,
        activity=act,
        evidence=bundle,
        camera_profile="VIEW_LEFT",
        procedure=demo_procedure,
    )

    assert decision.is_uncertain
    assert not decision.is_deviation
    assert decision.decision == DecisionType.UNCERTAIN

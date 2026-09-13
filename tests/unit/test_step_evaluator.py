"""Unit tests for StepEvaluator (D4.03)."""

import pytest

from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.procedure.evaluator import StepEvaluator
from core.procedure.schema import ExperimentStep
from core.procedure.types import StepCandidate, StepMatchStatus


@pytest.fixture
def evaluator():
    return StepEvaluator()


@pytest.fixture
def sample_step():
    return ExperimentStep(
        id="STEP_02",
        sequence=2,
        name="Grasp Specimen Red Box",
        expected_objects=["RED_BOX"],
        expected_actions=["GRASP"],
        required_evidence=["OBJECT_DETECTED", "HAND_OBJECT_CONTACT"],
        min_confidence=0.75,
        min_duration_seconds=1.5,
    )


def test_step_verified(evaluator, sample_step):
    cand = StepCandidate(
        step_id="STEP_02",
        activity_type="GRASP",
        object_id="RED_BOX",
        match_score=0.92,
        timestamp_start=2.0,
        timestamp_end=4.0,  # 2.0s duration >= 1.5s
    )
    bundle = EvidenceBundle(
        step_id="STEP_02",
        evidence_score=0.88,
        required_satisfied=True,
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.92))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.HAND_OBJECT_CONTACT, verified=True, confidence=0.85))

    decision = evaluator.evaluate_step(cand, bundle, sample_step)
    assert decision.status == StepMatchStatus.VERIFIED
    assert decision.confidence >= 0.75
    assert decision.step_id == "STEP_02"
    assert len(decision.reasons) > 0


def test_step_uncertain_missing_required(evaluator, sample_step):
    cand = StepCandidate(
        step_id="STEP_02",
        activity_type="GRASP",
        object_id="RED_BOX",
        match_score=0.85,
        timestamp_start=2.0,
        timestamp_end=4.0,
    )
    bundle = EvidenceBundle(
        step_id="STEP_02",
        evidence_score=0.60,
        required_satisfied=False,
        missing_required=["HAND_OBJECT_CONTACT"],
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.90))

    decision = evaluator.evaluate_step(cand, bundle, sample_step)
    assert decision.status == StepMatchStatus.UNCERTAIN
    assert "Missing required evidence" in decision.reasons[0]


def test_step_not_matched_id_mismatch(evaluator, sample_step):
    cand = StepCandidate(
        step_id="STEP_99",
        activity_type="GRASP",
        object_id="RED_BOX",
        match_score=0.90,
    )
    bundle = EvidenceBundle(step_id="STEP_99", evidence_score=0.85)

    decision = evaluator.evaluate_step(cand, bundle, sample_step)
    assert decision.status == StepMatchStatus.NOT_MATCHED
    assert "does not match target step" in decision.reasons[0]


def test_no_deviation_status_in_phase_4(evaluator, sample_step):
    """Ensures Phase 4 strictly never produces DEVIATION (Phase 5 responsibility)."""
    cand = StepCandidate(
        step_id="STEP_02",
        activity_type="GRASP",
        object_id="YELLOW_BOX",
        match_score=0.10,
    )
    bundle = EvidenceBundle(step_id="STEP_02", evidence_score=0.10, required_satisfied=False)

    decision = evaluator.evaluate_step(cand, bundle, sample_step)
    assert decision.status != "DEVIATION"
    assert decision.status in (StepMatchStatus.NOT_MATCHED, StepMatchStatus.UNCERTAIN)

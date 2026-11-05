"""A legacy stillness waiver must not waive unrelated verification gates."""
import pytest

from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.procedure.evaluator import StepEvaluator
from core.procedure.schema import ExperimentStep
from core.procedure.types import StepCandidate, StepMatchStatus


@pytest.mark.parametrize("failed_gate", ["evidence", "confidence", "duration", "sequence", None])
def test_destination_alone_cannot_bypass_gates(failed_gate):
    step = ExperimentStep(
        id="STEP_03", sequence=3, name="Placement", expected_actions=["PLACE"],
        expected_objects=["RED_BOX"], allow_unstable_placement=True,
        min_confidence=0.8, min_duration_seconds=1.0, action_sequence=["MOVE", "PLACE"],
    )
    candidate = StepCandidate(
        step_id="STEP_03", activity_type="PLACE", object_id="RED_BOX",
        match_score=0.1 if failed_gate == "confidence" else 0.95,
        timestamp_start=0, timestamp_end=0.1 if failed_gate == "duration" else 2,
        match_details={"primitives": [] if failed_gate == "sequence" else ["MOVE", "PLACE"]},
    )
    bundle = EvidenceBundle(
        required_satisfied=failed_gate != "evidence",
        missing_required=["OBJECT_DETECTED"] if failed_gate == "evidence" else [],
        evidence_score=0.1 if failed_gate == "confidence" else 0.95,
    )
    bundle.add_item(EvidenceItem(EvidenceType.DESTINATION_MATCH, True, 0.95))
    result = StepEvaluator().evaluate_step(candidate, bundle, step)
    assert (result.status == StepMatchStatus.VERIFIED) == (failed_gate is None)

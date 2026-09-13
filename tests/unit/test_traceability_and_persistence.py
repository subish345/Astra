"""Unit tests for StepTraceRecord (D4.07) and SQLite Persistence (D4.13)."""

import pytest

from core.activity.types import ActivityObservation, TemporalWindow
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.mission.database import DatabaseManager
from core.procedure.traceability import StepTraceRecord
from core.procedure.types import (
    ProcedureState,
    ProcedureStatus,
    StepCandidate,
    StepEvaluation,
    StepMatchStatus,
)


def test_step_trace_record_formatting():
    eval_rec = StepEvaluation(
        experiment_id="DEMO_EXP",
        run_id="RUN_001",
        step_id="STEP_02",
        status=StepMatchStatus.VERIFIED,
        confidence=0.92,
        evidence_bundle_id="BND_123",
        timestamp_start=2.0,
        timestamp_end=4.0,
        reasons=["Required evidence met"],
    )
    cand = StepCandidate(
        step_id="STEP_02",
        activity_type="GRASP",
        object_id="RED_BOX",
        match_score=0.94,
    )
    bundle = EvidenceBundle(
        bundle_id="BND_123",
        step_id="STEP_02",
        evidence_score=0.90,
        required_satisfied=True,
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.95))

    trace = StepTraceRecord(evaluation=eval_rec, candidate=cand, bundle=bundle)
    tree_text = trace.format_tree()

    assert "STEP AUDIT TRACE: [STEP_02] — ✓ VERIFIED" in tree_text
    assert "RED_BOX" in tree_text
    assert "OBJECT_DETECTED" in tree_text
    assert "Required evidence met" in tree_text

    d = trace.to_dict()
    assert d["evaluation"]["step_id"] == "STEP_02"
    assert d["candidate"]["match_score"] == 0.94


def test_sqlite_persistence(tmp_path):
    db_file = tmp_path / "test_astra.db"
    db = DatabaseManager(db_file)
    db.initialize()

    db.record_experiment("EXP_TEST", "Test Exp", "1.0.0")
    db.start_experiment_run("RUN_TEST", "EXP_TEST", total_steps=3)

    # 1. Record EvidenceBundle
    bundle = EvidenceBundle(
        bundle_id="BND_TEST_01",
        activity_id="ACT_01",
        step_id="STEP_01",
        activity_name="APPROACH",
        target_object_id="MAIN_BOX",
        timestamp=2.5,
        evidence_score=0.88,
        required_satisfied=True,
        source_frames=[10, 20],
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.92))
    db.record_evidence_bundle(bundle)

    # 2. Record StepEvaluation
    evaluation = StepEvaluation(
        evaluation_id="EVAL_TEST_01",
        experiment_id="EXP_TEST",
        run_id="RUN_TEST",
        step_id="STEP_01",
        status=StepMatchStatus.VERIFIED,
        confidence=0.91,
        evidence_bundle_id=bundle.bundle_id,
        timestamp_start=1.0,
        timestamp_end=2.5,
        reasons=["All required evidence confirmed"],
    )
    db.record_step_evaluation(evaluation)

    # 3. Record ProcedureProgress
    proc_state = ProcedureState(
        experiment_id="EXP_TEST",
        run_id="RUN_TEST",
        current_step="STEP_02",
        previous_step="STEP_01",
        completed_steps=["STEP_01"],
        procedure_status=ProcedureStatus.NEXT_STEP,
        timestamp=2.5,
    )
    db.record_procedure_progress(proc_state)

    # Verify retrieval
    retrieved = db.get_step_evaluations(run_id="RUN_TEST")
    assert len(retrieved) == 1
    rec = retrieved[0]
    assert rec["step_id"] == "STEP_01"
    assert rec["status"] == "VERIFIED"
    assert rec["confidence"] == 0.91
    assert rec["reasons"] == ["All required evidence confirmed"]

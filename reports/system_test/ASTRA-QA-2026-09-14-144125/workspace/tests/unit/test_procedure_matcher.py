"""Unit tests for ProcedureMatcher (D4.01)."""

import pytest

from core.activity.types import ActivityObservation, TemporalWindow
from core.procedure.matcher import ProcedureMatcher
from core.procedure.schema import (
    ExperimentDefinition,
    ExperimentMetadata,
    ExperimentObject,
    ExperimentStep,
)
from core.procedure.types import StepMatchStatus


@pytest.fixture
def sample_procedure():
    meta = ExperimentMetadata(id="TEST_EXP", name="Test Experiment", version="1.0.0")
    objects = [
        ExperimentObject(id="RED_BOX", name="Red Box"),
        ExperimentObject(id="YELLOW_BOX", name="Yellow Box"),
        ExperimentObject(id="MAIN_BOX", name="Main Box"),
    ]
    steps = [
        ExperimentStep(
            id="STEP_01",
            sequence=1,
            name="Approach Station",
            expected_objects=["MAIN_BOX"],
            expected_actions=["APPROACH"],
        ),
        ExperimentStep(
            id="STEP_02",
            sequence=2,
            name="Grasp Red Box",
            expected_objects=["RED_BOX"],
            expected_actions=["GRASP"],
        ),
        ExperimentStep(
            id="STEP_03",
            sequence=3,
            name="Move Red Box",
            expected_objects=["RED_BOX"],
            expected_actions=["MOVE"],
            repeatable=True,
        ),
    ]
    return ExperimentDefinition(experiment=meta, objects=objects, steps=steps)


def test_exact_match(sample_procedure):
    matcher = ProcedureMatcher()
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.95,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    candidates = matcher.match(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_02",
    )

    assert len(candidates) >= 1
    best = candidates[0]
    assert best.step_id == "STEP_02"
    assert best.activity_type == "GRASP"
    assert best.object_id == "RED_BOX"
    assert best.match_score > 0.85
    assert best.status == StepMatchStatus.CANDIDATE


def test_wrong_object_mismatch(sample_procedure):
    matcher = ProcedureMatcher()
    # Astronaut grasps YELLOW_BOX instead of expected RED_BOX
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="YELLOW_BOX",
        confidence=0.90,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    candidates = matcher.match(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_02",
    )

    # STEP_02 requires RED_BOX; YELLOW_BOX must NOT match STEP_02
    step_02_cand = next((c for c in candidates if c.step_id == "STEP_02"), None)
    assert step_02_cand is None


def test_action_mismatch(sample_procedure):
    matcher = ProcedureMatcher()
    obs = ActivityObservation(
        activity_name="POUR",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.90,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    candidates = matcher.match(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_02",
    )
    # Neither STEP_01 nor STEP_02 expects POUR
    assert len(candidates) == 0


def test_completed_step_exclusion(sample_procedure):
    matcher = ProcedureMatcher()
    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    # STEP_01 is completed and not repeatable
    candidates = matcher.match(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_02",
        completed_steps=["STEP_01"],
    )
    step_01_cand = next((c for c in candidates if c.step_id == "STEP_01"), None)
    assert step_01_cand is None


def test_repeatable_step_inclusion(sample_procedure):
    matcher = ProcedureMatcher()
    obs = ActivityObservation(
        activity_name="MOVE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.91,
        window=TemporalWindow(start_time=1.0, end_time=3.0),
    )
    # STEP_03 is repeatable: even if marked completed, it can be matched again
    candidates = matcher.match(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_03",
        completed_steps=["STEP_01", "STEP_02", "STEP_03"],
    )
    step_03_cand = next((c for c in candidates if c.step_id == "STEP_03"), None)
    assert step_03_cand is not None
    assert step_03_cand.step_id == "STEP_03"


def test_match_best_convenience(sample_procedure):
    matcher = ProcedureMatcher()
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.95,
        window=TemporalWindow(start_time=1.0, end_time=2.5),
    )
    best = matcher.match_best(
        activity=obs,
        procedure=sample_procedure,
        current_step_id="STEP_02",
    )
    assert best is not None
    assert best.step_id == "STEP_02"

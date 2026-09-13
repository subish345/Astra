"""Unit tests for ExpectedNextStepEngine (D4.05)."""

import pytest

from core.procedure.next_step import ExpectedNextStepEngine
from core.procedure.schema import (
    ExperimentDefinition,
    ExperimentMetadata,
    ExperimentObject,
    ExperimentStep,
)


@pytest.fixture
def branching_procedure():
    meta = ExperimentMetadata(id="BRANCH_EXP", name="Branching Experiment", version="1.0.0")
    steps = [
        ExperimentStep(
            id="STEP_01",
            sequence=1,
            name="Step 1",
            transitions=["STEP_02A", "STEP_02B"],
        ),
        ExperimentStep(
            id="STEP_02A",
            sequence=2,
            name="Step 2 Option A",
            transitions=[{"condition": "CONDITION_NORMAL", "next": "STEP_03"}],
        ),
        ExperimentStep(
            id="STEP_02B",
            sequence=3,
            name="Step 2 Option B",
            transitions=["STEP_03"],
        ),
        ExperimentStep(
            id="STEP_03",
            sequence=4,
            name="Step 3",
            optional=True,
            transitions=["STEP_04"],
        ),
        ExperimentStep(
            id="STEP_04",
            sequence=5,
            name="Final Step",
            transitions=[],
        ),
    ]
    return ExperimentDefinition(experiment=meta, steps=steps)


def test_initial_step(branching_procedure):
    engine = ExpectedNextStepEngine(branching_procedure)
    assert engine.get_initial_step() == "STEP_01"


def test_graph_transitions(branching_procedure):
    engine = ExpectedNextStepEngine(branching_procedure)
    allowed = engine.get_next_allowed_steps("STEP_01")
    assert allowed == ["STEP_02A", "STEP_02B"]
    assert engine.get_primary_expected_step("STEP_01") == "STEP_02A"


def test_conditional_branching(branching_procedure):
    engine = ExpectedNextStepEngine(branching_procedure)
    # Condition False -> no transition
    allowed_unmet = engine.get_next_allowed_steps("STEP_02A", runtime_conditions={"CONDITION_NORMAL": False})
    assert len(allowed_unmet) == 0

    # Condition True -> allowed
    allowed_met = engine.get_next_allowed_steps("STEP_02A", runtime_conditions={"CONDITION_NORMAL": True})
    assert allowed_met == ["STEP_03"]


def test_is_valid_transition(branching_procedure):
    engine = ExpectedNextStepEngine(branching_procedure)
    assert engine.is_valid_transition("STEP_01", "STEP_02B") is True
    assert engine.is_valid_transition("STEP_01", "STEP_04") is False


def test_sequence_order_fallback():
    meta = ExperimentMetadata(id="SEQ_EXP", name="Sequential Exp", version="1.0.0")
    steps = [
        ExperimentStep(id="S1", sequence=1, name="One"),
        ExperimentStep(id="S2", sequence=2, name="Two", optional=True),
        ExperimentStep(id="S3", sequence=3, name="Three"),
    ]
    proc = ExperimentDefinition(experiment=meta, steps=steps)
    engine = ExpectedNextStepEngine(proc)

    # From S1, S2 is next. Since S2 is optional, S3 is also allowed!
    allowed = engine.get_next_allowed_steps("S1")
    assert allowed == ["S2", "S3"]
    assert engine.get_primary_expected_step("S1") == "S2"

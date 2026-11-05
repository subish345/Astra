"""Unit tests for experiment schema definition and semantic validator."""

import pytest
import yaml

from core.procedure.schema import (
    ActionPrimitive,
    ExperimentDefinition,
    ExperimentMetadata,
    ExperimentObject,
    ExperimentStep,
    RecoveryInstruction,
)
from core.procedure.validator import (
    ProcedureValidationError,
    load_procedure_file,
    validate_experiment_definition,
)


def test_valid_demo_procedure_file():
    """Verify demo procedure YAML passes validation."""
    exp = load_procedure_file("configs/experiments/demo.yaml")
    assert exp.experiment.id == "DEMO_EXP_001"
    assert len(exp.steps) == 4
    assert len(exp.objects) == 4


def test_duplicate_object_id_rejected():
    """Duplicate object IDs must be rejected."""
    exp = ExperimentDefinition(
        experiment=ExperimentMetadata(id="TEST_001", name="Test"),
        objects=[
            ExperimentObject(id="BOX", name="Box 1"),
            ExperimentObject(id="BOX", name="Box 2"),
        ],
        steps=[
            ExperimentStep(
                id="STEP_01",
                sequence=1,
                name="Step 1",
                expected_objects=["BOX"],
                expected_actions=["APPROACH"],
                required_evidence=["object_visible"],
            )
        ],
    )
    errors = validate_experiment_definition(exp)
    assert any("Duplicate object ID" in e for e in errors)


def test_duplicate_step_id_rejected():
    """Duplicate step IDs must be rejected."""
    exp = ExperimentDefinition(
        experiment=ExperimentMetadata(id="TEST_001", name="Test"),
        objects=[ExperimentObject(id="BOX", name="Box 1")],
        steps=[
            ExperimentStep(
                id="STEP_01",
                sequence=1,
                name="Step 1",
                expected_objects=["BOX"],
                expected_actions=["APPROACH"],
                required_evidence=["object_visible"],
            ),
            ExperimentStep(
                id="STEP_01",
                sequence=2,
                name="Step 2",
                expected_objects=["BOX"],
                expected_actions=["GRASP"],
                required_evidence=["object_visible"],
            ),
        ],
    )
    errors = validate_experiment_definition(exp)
    assert any("Duplicate step ID" in e for e in errors)


def test_sequence_gap_rejected():
    """Step sequence numbers must start at 1 with no gaps."""
    exp = ExperimentDefinition(
        experiment=ExperimentMetadata(id="TEST_001", name="Test"),
        objects=[ExperimentObject(id="BOX", name="Box 1")],
        steps=[
            ExperimentStep(
                id="STEP_01",
                sequence=1,
                name="Step 1",
                expected_objects=["BOX"],
                expected_actions=["APPROACH"],
                required_evidence=["object_visible"],
            ),
            ExperimentStep(
                id="STEP_02",
                sequence=3,  # Gap: missing sequence 2
                name="Step 3",
                expected_objects=["BOX"],
                expected_actions=["GRASP"],
                required_evidence=["object_visible"],
            ),
        ],
    )
    errors = validate_experiment_definition(exp)
    assert any("consecutive starting at 1" in e for e in errors)


def test_undefined_object_reference_rejected():
    """Referencing an undefined object in expected_objects must be rejected."""
    exp = ExperimentDefinition(
        experiment=ExperimentMetadata(id="TEST_001", name="Test"),
        objects=[ExperimentObject(id="BOX", name="Box 1")],
        steps=[
            ExperimentStep(
                id="STEP_01",
                sequence=1,
                name="Step 1",
                expected_objects=["UNDEFINED_OBJ"],
                expected_actions=["APPROACH"],
                required_evidence=["object_visible"],
            )
        ],
    )
    errors = validate_experiment_definition(exp)
    assert any("references undefined object 'UNDEFINED_OBJ'" in e for e in errors)


def test_invalid_action_primitive_rejected():
    """Unknown action strings must fail Pydantic validation."""
    with pytest.raises(Exception):
        ExperimentStep(
            id="STEP_01",
            sequence=1,
            name="Step 1",
            expected_objects=["BOX"],
            expected_actions=["NON_EXISTENT_ACTION"],
            required_evidence=["object_visible"],
        )


def test_invalid_recovery_target_rejected():
    """Recovery target pointing to non-existent step must be rejected."""
    exp = ExperimentDefinition(
        experiment=ExperimentMetadata(id="TEST_001", name="Test"),
        objects=[ExperimentObject(id="BOX", name="Box 1")],
        steps=[
            ExperimentStep(
                id="STEP_01",
                sequence=1,
                name="Step 1",
                expected_objects=["BOX"],
                expected_actions=["APPROACH"],
                required_evidence=["object_visible"],
                recovery=RecoveryInstruction(instruction="Fix it", target_step="STEP_NON_EXISTENT"),
            )
        ],
    )
    errors = validate_experiment_definition(exp)
    assert any("references non-existent target step" in e for e in errors)

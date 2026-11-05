"""Procedure validation engine for ASTRA-EA.

Performs semantic and referential integrity checks on loaded experiment procedures.
Ensures that experiments are fully valid before execution begins.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import yaml
from pydantic import ValidationError

from core.procedure.schema import ExperimentDefinition


class ProcedureValidationError(Exception):
    """Raised when an experiment procedure violates structural or semantic rules."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Procedure validation failed with following errors:\n" + "\n".join(f" - {e}" for e in errors)
        super().__init__(message)


def validate_experiment_definition(exp: ExperimentDefinition) -> List[str]:
    """Perform semantic and relational validation on an ExperimentDefinition.

    Returns:
        List of error strings (empty if valid).
    """
    errors: List[str] = []

    # 1. Object ID uniqueness
    object_ids = set()
    for obj in exp.objects:
        if obj.id in object_ids:
            errors.append(f"Duplicate object ID defined: '{obj.id}'")
        object_ids.add(obj.id)

    # 2. Steps validation
    if not exp.steps:
        errors.append("Experiment definition contains no procedure steps.")
        return errors

    step_ids = set()
    sequences = []

    for step in exp.steps:
        # Step ID uniqueness
        if step.id in step_ids:
            errors.append(f"Duplicate step ID defined: '{step.id}'")
        step_ids.add(step.id)
        sequences.append(step.sequence)

        # Expected objects exist
        for obj_id in step.expected_objects:
            if obj_id not in object_ids:
                errors.append(f"Step '{step.id}' references undefined object '{obj_id}'")

        # Expected actions non-empty
        if not step.expected_actions:
            errors.append(f"Step '{step.id}' has empty expected_actions.")

        # Required evidence non-empty
        if not step.required_evidence:
            errors.append(f"Step '{step.id}' has empty required_evidence.")

        # Recovery target step validation
        if step.recovery and step.recovery.target_step:
            # We check target_step after all step IDs are gathered
            pass

    # Sequence ordering check (1, 2, 3, ...)
    sorted_seq = sorted(sequences)
    expected_seq = list(range(1, len(sequences) + 1))
    if sorted_seq != expected_seq:
        errors.append(f"Step sequence numbering must be consecutive starting at 1. Found: {sorted_seq}")

    # Second pass for recovery target steps
    for step in exp.steps:
        if step.recovery and step.recovery.target_step:
            if step.recovery.target_step not in step_ids:
                errors.append(
                    f"Step '{step.id}' recovery references non-existent target step '{step.recovery.target_step}'"
                )

    return errors


def load_procedure_file(file_path: str | Path) -> ExperimentDefinition:
    """Load and strictly validate a YAML procedure file.

    Args:
        file_path: Path to the YAML procedure configuration.

    Returns:
        Validated ExperimentDefinition instance.

    Raises:
        FileNotFoundError: If file does not exist.
        ProcedureValidationError: If syntactic or semantic validation fails.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Experiment procedure file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            raw_data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ProcedureValidationError([f"YAML syntax error: {exc}"])

    if not isinstance(raw_data, dict):
        raise ProcedureValidationError(["Procedure file root must be a YAML mapping/dictionary."])

    try:
        exp_def = ExperimentDefinition(**raw_data)
    except ValidationError as exc:
        schema_errors = [f"{err['loc']}: {err['msg']}" for err in exc.errors()]
        raise ProcedureValidationError(schema_errors)

    semantic_errors = validate_experiment_definition(exp_def)
    if semantic_errors:
        raise ProcedureValidationError(semantic_errors)

    return exp_def

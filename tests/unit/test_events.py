"""Unit tests for telemetry event contracts and serialization."""

import json
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from core.mission.events import (
    ActivityEvent,
    AlertEvent,
    AssistantPriority,
    DecisionType,
    DeviationReason,
    EvidenceEvent,
    HealthEvent,
    HealthState,
    ProcedureDecision,
)


def test_procedure_decision_serialization():
    """Verify serialization and deserialization roundtrip for ProcedureDecision."""
    decision = ProcedureDecision(
        experiment_id="DEMO_EXP_001",
        step_id="STEP_02",
        sequence=2,
        decision=DecisionType.DEVIATION,
        deviation_reason=DeviationReason.WRONG_OBJECT,
        confidence=0.89,
        reason="Astronaut grasped YELLOW_BOX instead of RED_BOX",
    )

    data_json = decision.model_dump_json()
    assert "WRONG_OBJECT" in data_json
    assert "DEVIATION" in data_json

    restored = ProcedureDecision.model_validate_json(data_json)
    assert restored.decision == DecisionType.DEVIATION
    assert restored.deviation_reason == DeviationReason.WRONG_OBJECT
    assert restored.confidence == pytest.approx(0.89)


def test_invalid_decision_type_rejected():
    """Invalid decision strings must fail validation."""
    with pytest.raises(ValidationError):
        ProcedureDecision(
            experiment_id="DEMO_EXP_001",
            step_id="STEP_01",
            sequence=1,
            decision="INVALID_STATE",  # type: ignore[arg-type]
            confidence=0.9,
        )


def test_invalid_confidence_range_rejected():
    """Confidence out of [0.0, 1.0] must fail validation."""
    with pytest.raises(ValidationError):
        ProcedureDecision(
            experiment_id="DEMO_EXP_001",
            step_id="STEP_01",
            sequence=1,
            decision=DecisionType.VERIFIED,
            confidence=1.5,  # Exceeds 1.0
        )


def test_evidence_event_structure():
    """Verify EvidenceEvent item dictionary handling."""
    evd = EvidenceEvent(
        activity_ref="ACT_12345678",
        evidence_score=0.95,
        items={
            "object_detected": True,
            "hand_detected": True,
            "contact_detected": True,
            "motion_coupled": True,
        },
        is_conclusive=True,
    )
    assert evd.items["contact_detected"] is True
    assert evd.is_conclusive is True
    dump = evd.model_dump()
    assert dump["evidence_score"] == pytest.approx(0.95)

"""Unit tests for MultimodalEvidenceEngine and EvidenceBundle (D4.02)."""

import pytest

from core.activity.types import ActivityObservation, TemporalWindow
from core.evidence.engine import MultimodalEvidenceEngine
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.interaction.types import HandType, InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import BoundingBox, PerceptionState, Track, TrackState
from core.procedure.schema import EvidencePathRule, ExperimentStep


@pytest.fixture
def evidence_engine():
    return MultimodalEvidenceEngine()


@pytest.fixture
def dummy_step():
    return ExperimentStep(
        id="STEP_02",
        sequence=2,
        name="Grasp Red Box",
        expected_objects=["RED_BOX"],
        expected_actions=["GRASP"],
        required_evidence=["OBJECT_DETECTED", "HAND_OBJECT_CONTACT", "TEMPORAL_CONSISTENCY"],
        optional_evidence=["COUPLED_MOTION", "POSE_CONSISTENCY"],
        min_confidence=0.75,
        min_duration_seconds=1.5,
    )


def test_all_required_evidence_present(evidence_engine, dummy_step):
    track = Track(
        track_id=1,
        class_name="RED_BOX",
        confidence=0.92,
        bbox=BoundingBox(0.3, 0.3, 0.2, 0.2),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(timestamp=5.0, frame_id=50, source_id="CAM_0", tracks=[track])
    int_ev = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=1,
        hand_type=HandType.RIGHT,
        state=InteractionState.CONTACT,
        distance=0.08,
        confidence=0.88,
        timestamp=5.0,
    )
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.91,
        window=TemporalWindow(start_time=3.0, end_time=5.0),
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        interactions=[int_ev],
        tracks=[track],
        perception_state=p_state,
        step=dummy_step,
    )

    assert bundle.required_satisfied is True
    assert len(bundle.missing_required) == 0
    assert bundle.evidence_score >= 0.75
    assert bundle.items[EvidenceType.OBJECT_DETECTED.value].verified is True
    assert bundle.items[EvidenceType.HAND_OBJECT_CONTACT.value].verified is True
    assert bundle.items[EvidenceType.TEMPORAL_CONSISTENCY.value].verified is True


def test_one_required_item_missing(evidence_engine, dummy_step):
    track = Track(
        track_id=1,
        class_name="RED_BOX",
        confidence=0.92,
        bbox=BoundingBox(0.3, 0.3, 0.2, 0.2),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(timestamp=5.0, frame_id=50, source_id="CAM_0", tracks=[track])
    # No interaction (no contact)
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.91,
        window=TemporalWindow(start_time=3.0, end_time=5.0),
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        interactions=[],
        tracks=[track],
        perception_state=p_state,
        step=dummy_step,
    )

    assert bundle.required_satisfied is False
    assert any("CONTACT" in m for m in bundle.missing_required)


def test_temporal_duration_inconsistency(evidence_engine, dummy_step):
    # Duration is 0.5s, while dummy_step min_duration_seconds is 1.5s
    obs = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.90,
        window=TemporalWindow(start_time=4.5, end_time=5.0),
    )
    track = Track(
        track_id=1,
        class_name="RED_BOX",
        confidence=0.92,
        bbox=BoundingBox(0.3, 0.3, 0.2, 0.2),
        state=TrackState.VISIBLE,
    )
    bundle = evidence_engine.evaluate(activity=obs, tracks=[track], step=dummy_step)
    temp_item = bundle.items[EvidenceType.TEMPORAL_CONSISTENCY.value]
    assert temp_item.verified is False


def test_alternate_evidence_paths_any_of(evidence_engine):
    step_with_alt = ExperimentStep(
        id="STEP_ALT",
        sequence=1,
        name="Alternate Evidence Test",
        expected_objects=["RED_BOX"],
        expected_actions=["MOVE"],
        evidence_paths=EvidencePathRule(
            any_of=[
                ["OBJECT_DETECTED", "HAND_OBJECT_CONTACT"],
                ["OBJECT_DETECTED", "COUPLED_MOTION"],
            ]
        ),
    )

    bundle = EvidenceBundle(step_id="STEP_ALT", target_object_id="RED_BOX", confidence=0.88)
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.90))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.HAND_OBJECT_CONTACT, verified=False, confidence=0.20))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.COUPLED_MOTION, verified=True, confidence=0.85))

    sat, missing = evidence_engine.evaluate_evidence_paths(bundle, step_with_alt.evidence_paths)
    # Second path [OBJECT_DETECTED, COUPLED_MOTION] is satisfied
    assert sat is True
    assert len(missing) == 0


def test_alternate_evidence_paths_all_of(evidence_engine):
    rule = EvidencePathRule(all_of=["OBJECT_DETECTED", "ACTOR_DETECTED"])
    bundle = EvidenceBundle()
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.90))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=False, confidence=0.10))

    sat, missing = evidence_engine.evaluate_evidence_paths(bundle, rule)
    assert sat is False
    assert "ACTOR_DETECTED" in missing

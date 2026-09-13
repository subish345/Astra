"""Unit tests for Phase 4.1: Procedure Semantics & Evidence Correction.

Verifies:
1. Step 1 spatial/zone approach semantics (far-away, zone entry, temporal presence).
2. Step 3 destination matching and physical stabilization (movement alone fails, reaches surface but moving fails, stabilized succeeds).
3. Step 4 contact clearance (active contact rejected, 1-frame drop rejected, cleared >= 0.5s verified).
4. Canonical evidence vocabulary normalization and aliases.
5. Action sequence validation and causal traceability tree.
"""

import pytest
import yaml
from pathlib import Path

from core.activity.types import ActivityObservation, ActivityStatus, TemporalWindow
from core.evidence.engine import MultimodalEvidenceEngine
from core.evidence.types import (
    EvidenceBundle,
    EvidenceItem,
    EvidenceType,
    normalize_evidence_name,
)
from core.interaction.types import InteractionEvent, InteractionState
from core.perception.types import BoundingBox, HandType, PerceptionState, PoseObservation, Track, TrackState
from core.procedure.evaluator import StepEvaluator
from core.procedure.matcher import ProcedureMatcher
from core.procedure.progress import ProcedureProgressManager
from core.procedure.schema import ExperimentDefinition, ExperimentStep, ZoneDefinition, DestinationRule, StabilizationRule
from core.procedure.traceability import StepTraceRecord
from core.procedure.types import StepCandidate, StepMatchStatus, ProcedureStatus


@pytest.fixture
def demo_procedure() -> ExperimentDefinition:
    path = Path("configs/experiments/demo.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ExperimentDefinition(**data)


@pytest.fixture
def evidence_engine() -> MultimodalEvidenceEngine:
    engine = MultimodalEvidenceEngine()
    engine.reset()
    return engine


@pytest.fixture
def step_evaluator() -> StepEvaluator:
    return StepEvaluator()


# ==============================================================================
# STEP 1 TESTS: SPATIAL PROXIMITY & ZONE PRESENCE
# ==============================================================================

def test_step1_far_away_not_verified(demo_procedure, evidence_engine, step_evaluator):
    """Astronaut visible + box visible but far away -> NOT VERIFIED."""
    step_01 = demo_procedure.steps[0]

    # Person at top-right, box at bottom-left (normalized distance ~0.99)
    person = PoseObservation(
        person_id=1,
        keypoints=[],
        confidence=0.92,
        bbox=BoundingBox(0.85, 0.85, 0.98, 0.98),
    )
    box_track = Track(
        track_id=1,
        class_name="MAIN_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.05, 0.05, 0.15, 0.15),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=2.5,
        frame_id=30,
        source_id="CAM_0",
        tracks=[box_track],
        persons=[person],
    )

    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.88,
        window=TemporalWindow(start_time=0.0, end_time=2.5),
        status=ActivityStatus.IN_PROGRESS,
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[box_track],
        perception_state=p_state,
        step=step_01,
    )

    # Spatial proximity must NOT be verified when far away
    assert bundle.items[EvidenceType.SPATIAL_PROXIMITY.value].verified is False
    assert bundle.required_satisfied is False
    assert "SPATIAL_PROXIMITY" in bundle.missing_required

    candidate = StepCandidate(
        step_id="STEP_01",
        activity_type="APPROACH",
        object_id="MAIN_BOX",
        match_score=0.90,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=0.0,
        timestamp_end=2.5,
    )

    eval_result = step_evaluator.evaluate_step(
        candidate=candidate,
        bundle=bundle,
        step=step_01,
    )

    # Must NOT be VERIFIED
    assert eval_result.status != StepMatchStatus.VERIFIED


def test_step1_enters_zone_short_duration_verifying(demo_procedure, evidence_engine, step_evaluator):
    """Astronaut enters station zone but has not reached 2.0s duration -> UNCERTAIN / not verified."""
    step_01 = demo_procedure.steps[0]

    # Person close to box inside station zone
    person = PoseObservation(
        person_id=1,
        keypoints=[],
        confidence=0.92,
        bbox=BoundingBox(0.20, 0.20, 0.35, 0.45),
    )
    box_track = Track(
        track_id=1,
        class_name="MAIN_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.25, 0.25, 0.15, 0.15),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=0.5,
        frame_id=10,
        source_id="CAM_0",
        tracks=[box_track],
        persons=[person],
    )

    # Duration is only 0.5s (step requires 2.0s)
    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.88,
        window=TemporalWindow(start_time=0.0, end_time=0.5),
        status=ActivityStatus.IN_PROGRESS,
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[box_track],
        perception_state=p_state,
        step=step_01,
    )

    # Proximity is True, but TEMPORAL_PRESENCE must be False
    assert bundle.items[EvidenceType.SPATIAL_PROXIMITY.value].verified is True
    assert bundle.items[EvidenceType.TEMPORAL_PRESENCE.value].verified is False
    assert bundle.required_satisfied is False

    candidate = StepCandidate(
        step_id="STEP_01",
        activity_type="APPROACH",
        object_id="MAIN_BOX",
        match_score=0.90,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=0.0,
        timestamp_end=0.5,
    )

    eval_result = step_evaluator.evaluate_step(
        candidate=candidate,
        bundle=bundle,
        step=step_01,
    )
    assert eval_result.status != StepMatchStatus.VERIFIED


def test_step1_remains_in_zone_verified(demo_procedure, evidence_engine, step_evaluator):
    """Astronaut enters station zone and remains for >= 2.0s -> VERIFIED."""
    step_01 = demo_procedure.steps[0]

    person = PoseObservation(
        person_id=1,
        keypoints=[],
        confidence=0.95,
        bbox=BoundingBox(0.20, 0.20, 0.35, 0.45),
    )
    box_track = Track(
        track_id=1,
        class_name="MAIN_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.25, 0.25, 0.15, 0.15),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=2.8,
        frame_id=60,
        source_id="CAM_0",
        tracks=[box_track],
        persons=[person],
    )

    # Duration is 2.8s >= 2.0s
    obs = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=0.0, end_time=2.8),
        status=ActivityStatus.CONFIRMED,
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[box_track],
        perception_state=p_state,
        step=step_01,
    )

    assert bundle.items[EvidenceType.ACTOR_DETECTED.value].verified is True
    assert bundle.items[EvidenceType.OBJECT_DETECTED.value].verified is True
    assert bundle.items[EvidenceType.SPATIAL_PROXIMITY.value].verified is True
    assert bundle.items[EvidenceType.TEMPORAL_PRESENCE.value].verified is True
    assert bundle.required_satisfied is True

    candidate = StepCandidate(
        step_id="STEP_01",
        activity_type="APPROACH",
        object_id="MAIN_BOX",
        match_score=0.95,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=0.0,
        timestamp_end=2.8,
    )

    eval_result = step_evaluator.evaluate_step(
        candidate=candidate,
        bundle=bundle,
        step=step_01,
    )
    assert eval_result.status == StepMatchStatus.VERIFIED


# ==============================================================================
# STEP 3 TESTS: DESTINATION MATCHING & PHYSICAL STABILIZATION
# ==============================================================================

def test_step3_coupled_motion_without_destination_not_verified(demo_procedure, evidence_engine, step_evaluator):
    """Red box moves with hand but never reaches work surface -> NOT VERIFIED."""
    step_03 = demo_procedure.steps[2]

    # Red box is moving, but its location is far from WORK_SURFACE
    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.94,
        bbox=BoundingBox(0.10, 0.10, 0.12, 0.12),  # far from work surface
        state=TrackState.VISIBLE,
    )
    work_surface = Track(
        track_id=4,
        class_name="WORK_SURFACE",
        confidence=0.90,
        bbox=BoundingBox(0.60, 0.60, 0.25, 0.25),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=8.0,
        frame_id=120,
        source_id="CAM_0",
        tracks=[red_box, work_surface],
    )

    obs = ActivityObservation(
        activity_name="MOVE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.91,
        window=TemporalWindow(start_time=4.0, end_time=8.0),
        metadata={"in_contact": True, "moving": True},
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[red_box, work_surface],
        perception_state=p_state,
        step=step_03,
    )

    # COUPLED_MOTION is verified, but DESTINATION_MATCH is False
    assert bundle.items[EvidenceType.COUPLED_MOTION.value].verified is True
    assert bundle.items[EvidenceType.DESTINATION_MATCH.value].verified is False
    assert bundle.required_satisfied is False
    assert "DESTINATION_MATCH" in bundle.missing_required

    candidate = StepCandidate(
        step_id="STEP_03",
        activity_type="MOVE",
        object_id="RED_BOX",
        match_score=0.90,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=4.0,
        timestamp_end=8.0,
    )
    eval_result = step_evaluator.evaluate_step(candidate, bundle, step_03)
    assert eval_result.status != StepMatchStatus.VERIFIED


def test_step3_reaches_destination_but_keeps_moving_not_verified(demo_procedure, evidence_engine, step_evaluator):
    """Red box reaches surface but is still moving (not stabilized) -> NOT VERIFIED."""
    step_03 = demo_procedure.steps[2]

    # Red box center is right at work surface center, but velocity is high
    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.94,
        bbox=BoundingBox(0.50, 0.50, 0.12, 0.12),
        velocity=(28.0, 15.0),  # High velocity!
        state=TrackState.VISIBLE,
    )
    work_surface = Track(
        track_id=4,
        class_name="WORK_SURFACE",
        confidence=0.90,
        bbox=BoundingBox(0.48, 0.48, 0.25, 0.25),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=8.5,
        frame_id=140,
        source_id="CAM_0",
        tracks=[red_box, work_surface],
    )

    obs = ActivityObservation(
        activity_name="MOVE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=5.0, end_time=8.5),
        metadata={"in_contact": True, "moving": True, "destination_match": True, "stabilized": False},
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[red_box, work_surface],
        perception_state=p_state,
        step=step_03,
    )

    assert bundle.items[EvidenceType.DESTINATION_MATCH.value].verified is True
    # Object is still moving fast -> OBJECT_STABILIZED must be False
    assert bundle.items[EvidenceType.OBJECT_STABILIZED.value].verified is False
    assert bundle.required_satisfied is False

    candidate = StepCandidate(
        step_id="STEP_03",
        activity_type="MOVE",
        object_id="RED_BOX",
        match_score=0.90,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=5.0,
        timestamp_end=8.5,
    )
    eval_result = step_evaluator.evaluate_step(candidate, bundle, step_03)
    assert eval_result.status != StepMatchStatus.VERIFIED


def test_step3_reaches_destination_and_stabilizes_verified(demo_procedure, evidence_engine, step_evaluator):
    """Red box reaches surface and is stabilized -> VERIFIED."""
    step_03 = demo_procedure.steps[2]

    # Stationary at work surface
    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.50, 0.50, 0.12, 0.12),
        velocity=(0.0, 0.0),
        state=TrackState.VISIBLE,
    )
    work_surface = Track(
        track_id=4,
        class_name="WORK_SURFACE",
        confidence=0.92,
        bbox=BoundingBox(0.48, 0.48, 0.25, 0.25),
        state=TrackState.VISIBLE,
    )
    p_state = PerceptionState(
        timestamp=9.0,
        frame_id=160,
        source_id="CAM_0",
        tracks=[red_box, work_surface],
    )

    obs = ActivityObservation(
        activity_name="PLACE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.94,
        window=TemporalWindow(start_time=5.0, end_time=9.0),
        metadata={
            "in_contact": True,
            "destination_match": True,
            "object_stabilized": True,
            "primitives": ["LIFT", "MOVE", "APPROACH_DESTINATION", "PLACE"],
        },
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        tracks=[red_box, work_surface],
        perception_state=p_state,
        step=step_03,
    )

    assert bundle.items[EvidenceType.OBJECT_DETECTED.value].verified is True
    assert bundle.items[EvidenceType.COUPLED_MOTION.value].verified is True
    assert bundle.items[EvidenceType.DESTINATION_MATCH.value].verified is True
    assert bundle.items[EvidenceType.OBJECT_STABILIZED.value].verified is True
    assert bundle.required_satisfied is True

    candidate = StepCandidate(
        step_id="STEP_03",
        activity_type="PLACE",
        object_id="RED_BOX",
        match_score=0.95,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=5.0,
        timestamp_end=9.0,
        match_details={"primitives": ["LIFT", "MOVE", "APPROACH_DESTINATION", "PLACE"]},
    )
    eval_result = step_evaluator.evaluate_step(candidate, bundle, step_03)
    assert eval_result.status == StepMatchStatus.VERIFIED


# ==============================================================================
# STEP 4 TESTS: CONTACT CLEARANCE VS ACTIVE CONTACT
# ==============================================================================

def test_step4_active_contact_fails_release(demo_procedure, evidence_engine, step_evaluator):
    """Hand remains in active contact with Red Box -> RELEASE NOT VERIFIED."""
    step_04 = demo_procedure.steps[3]

    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.50, 0.50, 0.12, 0.12),
        state=TrackState.VISIBLE,
    )

    # Active contact interaction event
    int_ev = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=2,
        hand_type=HandType.RIGHT,
        state=InteractionState.GRASPING,
        confidence=0.92,
        distance=0.04,
        timestamp=12.0,
    )

    obs = ActivityObservation(
        activity_name="RELEASE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.85,
        window=TemporalWindow(start_time=10.0, end_time=12.0),
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        interactions=[int_ev],
        tracks=[red_box],
        step=step_04,
    )

    # Active contact is present -> CONTACT_CLEARED must be False!
    assert bundle.items[EvidenceType.HAND_OBJECT_CONTACT.value].verified is True
    assert bundle.items[EvidenceType.CONTACT_CLEARED.value].verified is False
    assert bundle.required_satisfied is False
    assert "CONTACT_CLEARED" in bundle.missing_required

    candidate = StepCandidate(
        step_id="STEP_04",
        activity_type="RELEASE",
        object_id="RED_BOX",
        match_score=0.88,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=10.0,
        timestamp_end=12.0,
    )
    eval_result = step_evaluator.evaluate_step(candidate, bundle, step_04)
    assert eval_result.status != StepMatchStatus.VERIFIED


def test_step4_contact_temporary_drop_one_frame_not_verified(demo_procedure, evidence_engine, step_evaluator):
    """Contact temporarily drops for < 0.5s -> CONTACT_CLEARED not verified."""
    step_04 = demo_procedure.steps[3]

    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.50, 0.50, 0.12, 0.12),
        state=TrackState.VISIBLE,
    )

    # 1. Establish prior contact
    evidence_engine.evaluate(
        interactions=[
            InteractionEvent(
                target_object_id="RED_BOX",
                target_track_id=2,
                hand_type=HandType.RIGHT,
                state=InteractionState.GRASPING,
                confidence=0.92,
                distance=0.04,
                timestamp=10.0,
            )
        ],
        tracks=[red_box],
        perception_state=PerceptionState(timestamp=10.0, frame_id=100, source_id="CAM_0", tracks=[red_box]),
    )

    # 2. Next frame at t=10.033 (33ms later, 1 frame dropout)
    p_state = PerceptionState(timestamp=10.033, frame_id=101, source_id="CAM_0", tracks=[red_box])
    obs = ActivityObservation(
        activity_name="HOLD",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.80,
        window=TemporalWindow(start_time=10.0, end_time=10.033),
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        interactions=[],  # Dropped contact in this single frame!
        tracks=[red_box],
        perception_state=p_state,
        step=step_04,
    )

    # Clearance duration is only 33ms (< 0.5s) -> CONTACT_CLEARED must be False
    assert bundle.items[EvidenceType.CONTACT_CLEARED.value].verified is False
    assert bundle.required_satisfied is False


def test_step4_contact_cleared_confirmed_duration_verified(demo_procedure, evidence_engine, step_evaluator):
    """Contact clears and persists cleared >= 0.5s while object is tracked -> RELEASE VERIFIED."""
    step_04 = demo_procedure.steps[3]

    red_box = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.50, 0.50, 0.12, 0.12),
        state=TrackState.VISIBLE,
    )

    # 1. Establish prior contact
    evidence_engine.evaluate(
        interactions=[
            InteractionEvent(
                target_object_id="RED_BOX",
                target_track_id=2,
                hand_type=HandType.RIGHT,
                state=InteractionState.GRASPING,
                confidence=0.95,
                distance=0.04,
                timestamp=10.0,
            )
        ],
        tracks=[red_box],
        perception_state=PerceptionState(timestamp=10.0, frame_id=100, source_id="CAM_0", tracks=[red_box]),
    )

    # 2. After hand withdrawal at t=11.0 (1.0s of contact clearance)
    p_state = PerceptionState(timestamp=11.0, frame_id=130, source_id="CAM_0", tracks=[red_box])
    obs = ActivityObservation(
        activity_name="RELEASE",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.95,
        window=TemporalWindow(start_time=10.0, end_time=11.0),
        status=ActivityStatus.CONFIRMED,
    )

    bundle = evidence_engine.evaluate(
        activity=obs,
        interactions=[],  # Cleared!
        tracks=[red_box],
        perception_state=p_state,
        step=step_04,
    )

    assert bundle.items[EvidenceType.OBJECT_DETECTED.value].verified is True
    assert bundle.items[EvidenceType.CONTACT_CLEARED.value].verified is True
    assert bundle.required_satisfied is True

    candidate = StepCandidate(
        step_id="STEP_04",
        activity_type="RELEASE",
        object_id="RED_BOX",
        match_score=0.95,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=10.0,
        timestamp_end=11.0,
    )
    eval_result = step_evaluator.evaluate_step(candidate, bundle, step_04)
    assert eval_result.status == StepMatchStatus.VERIFIED


# ==============================================================================
# CANONICAL VOCABULARY & ALIAS NORMALIZATION TESTS
# ==============================================================================

def test_canonical_evidence_vocabulary_normalization():
    """Verify legacy aliases normalize to canonical identifiers."""
    assert normalize_evidence_name("astronaut_visible") == "ACTOR_DETECTED"
    assert normalize_evidence_name("OBJECT_VISIBLE") == "OBJECT_DETECTED"
    assert normalize_evidence_name("contact_detected") == "HAND_OBJECT_CONTACT"
    assert normalize_evidence_name("motion_coupled") == "COUPLED_MOTION"
    assert normalize_evidence_name("released") == "CONTACT_CLEARED"
    assert normalize_evidence_name("destination_reached") == "DESTINATION_MATCH"
    assert normalize_evidence_name("object_stable") == "OBJECT_STABILIZED"
    assert normalize_evidence_name("STATION_PROXIMITY") == "SPATIAL_PROXIMITY"
    assert normalize_evidence_name("PRESENCE_CONFIRMED") == "TEMPORAL_PRESENCE"


def test_bundle_check_requirement_resolves_aliases():
    """Verify EvidenceBundle.check_requirement resolves aliases seamlessly."""
    bundle = EvidenceBundle(activity_id="A1", activity_name="TEST")
    bundle.add_item(
        EvidenceItem(evidence_type=EvidenceType.ACTOR_DETECTED, verified=True, confidence=0.9)
    )
    bundle.add_item(
        EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.9)
    )
    bundle.add_item(
        EvidenceItem(evidence_type=EvidenceType.CONTACT_CLEARED, verified=True, confidence=0.9)
    )

    # Check via canonical
    assert bundle.check_requirement("ACTOR_DETECTED") is True
    assert bundle.check_requirement("OBJECT_DETECTED") is True
    assert bundle.check_requirement("CONTACT_CLEARED") is True

    # Check via legacy aliases
    assert bundle.check_requirement("astronaut_visible") is True
    assert bundle.check_requirement("object_visible") is True
    assert bundle.check_requirement("released") is True


# ==============================================================================
# ACTION SEQUENCE & AUDIT TRACEABILITY TESTS
# ==============================================================================

def test_action_sequence_enforcement_and_trace_tree(demo_procedure, evidence_engine, step_evaluator):
    """Verify action sequence enforcement and tree formatting."""
    step_03 = demo_procedure.steps[2]
    assert step_03.action_sequence == ["LIFT", "MOVE", "APPROACH_DESTINATION", "PLACE"]

    bundle = EvidenceBundle(
        activity_id="A3",
        activity_name="PLACE",
        target_object_id="RED_BOX",
        evidence_score=0.92,
        required_satisfied=True,
    )
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_DETECTED, verified=True, confidence=0.92))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.COUPLED_MOTION, verified=True, confidence=0.90))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.DESTINATION_MATCH, verified=True, confidence=0.91))
    bundle.add_item(EvidenceItem(evidence_type=EvidenceType.OBJECT_STABILIZED, verified=True, confidence=0.90))

    candidate = StepCandidate(
        step_id="STEP_03",
        activity_type="PLACE",
        object_id="RED_BOX",
        match_score=0.95,
        status=StepMatchStatus.CANDIDATE,
        timestamp_start=5.0,
        timestamp_end=9.0,
        match_details={"primitives": ["LIFT", "MOVE", "APPROACH_DESTINATION", "PLACE"]},
    )

    evaluation = step_evaluator.evaluate_step(candidate, bundle, step_03)
    assert evaluation.status == StepMatchStatus.VERIFIED

    trace = StepTraceRecord(
        evaluation=evaluation,
        candidate=candidate,
        bundle=bundle,
        activity=ActivityObservation(
            activity_name="PLACE",
            actor="ASTRONAUT",
            target_object_id="RED_BOX",
            confidence=0.92,
            window=TemporalWindow(start_time=5.0, end_time=9.0),
        ),
    )

    tree = trace.format_tree()
    assert "STEP AUDIT TRACE: [STEP_03]" in tree
    assert "Action Sequence:" in tree
    assert "Expected: LIFT → MOVE → APPROACH_DESTINATION → PLACE" in tree
    assert "Sub-Actions: LIFT ✓, MOVE ✓, APPROACH_DESTINATION ✓, PLACE ✓" in tree
    assert "DESTINATION_MATCH: conf=0.91" in tree
    assert "OBJECT_STABILIZED: conf=0.90" in tree
    assert "VERIFIED" in tree

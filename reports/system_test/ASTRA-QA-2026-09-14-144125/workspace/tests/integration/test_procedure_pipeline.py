"""End-to-end procedural integration test (D4.09, Section 40).

Verifies full chain:
Perception -> Interaction -> Activity -> Evidence -> Procedure Matcher -> Step Evaluator -> Procedure Progress.
"""

import pytest

from core.activity.types import ActivityObservation, TemporalWindow
from core.evidence.engine import MultimodalEvidenceEngine
from core.interaction.types import HandType, InteractionEvent, InteractionState, SpatialRelationship
from core.perception.types import BoundingBox, HandObservation, PerceptionState, Track, TrackState
from core.procedure.progress import ProcedureProgressManager
from core.procedure.validator import load_procedure_file


@pytest.fixture
def demo_procedure():
    return load_procedure_file("configs/experiments/demo.yaml")


def test_full_procedural_pipeline_integration(demo_procedure):
    progress_mgr = ProcedureProgressManager(procedure=demo_procedure, run_id="INTEG_RUN_001")
    evidence_engine = MultimodalEvidenceEngine()

    assert progress_mgr.current_step == "STEP_01"

    # -------------------------------------------------------------
    # Scenario 1: Astronaut approaches MAIN_BOX (Satisfies STEP_01)
    # -------------------------------------------------------------
    main_track = Track(
        track_id=1,
        class_name="MAIN_BOX",
        confidence=0.92,
        bbox=BoundingBox(0.2, 0.2, 0.4, 0.4),
        state=TrackState.VISIBLE,
    )
    p_state_1 = PerceptionState(timestamp=2.5, frame_id=75, source_id="CAM_0", tracks=[main_track])

    act_1 = ActivityObservation(
        activity_name="APPROACH",
        actor="ASTRONAUT",
        target_object_id="MAIN_BOX",
        confidence=0.92,
        window=TemporalWindow(start_time=0.0, end_time=2.5),
    )

    bundle_1 = evidence_engine.evaluate(
        activity=act_1,
        tracks=[main_track],
        perception_state=p_state_1,
        step=progress_mgr._step_map.get("STEP_01"),
    )

    state_1 = progress_mgr.update(activity=act_1, bundle=bundle_1, timestamp=2.5)

    assert "STEP_01" in state_1.completed_steps
    assert state_1.current_step == "STEP_02"
    assert state_1.next_expected_step == "STEP_03"

    # -------------------------------------------------------------
    # Scenario 2: Astronaut grasps RED_BOX (Satisfies STEP_02)
    # -------------------------------------------------------------
    red_track = Track(
        track_id=2,
        class_name="RED_BOX",
        confidence=0.95,
        bbox=BoundingBox(0.4, 0.4, 0.2, 0.2),
        state=TrackState.VISIBLE,
    )
    hand_2 = HandObservation(hand_type=HandType.RIGHT, keypoints=[], confidence=0.92, wrist=(0.42, 0.42))
    p_state_2 = PerceptionState(timestamp=5.0, frame_id=150, source_id="CAM_0", tracks=[red_track], hands=[hand_2])

    int_2 = InteractionEvent(
        target_object_id="RED_BOX",
        target_track_id=2,
        hand_type=HandType.RIGHT,
        state=InteractionState.GRASPING,
        distance=0.04,
        confidence=0.90,
        timestamp=5.0,
    )

    act_2 = ActivityObservation(
        activity_name="GRASP",
        actor="ASTRONAUT",
        target_object_id="RED_BOX",
        confidence=0.94,
        window=TemporalWindow(start_time=3.0, end_time=5.0),
    )

    bundle_2 = evidence_engine.evaluate(
        activity=act_2,
        interactions=[int_2],
        tracks=[red_track],
        perception_state=p_state_2,
        step=progress_mgr._step_map.get("STEP_02"),
    )

    state_2 = progress_mgr.update(activity=act_2, bundle=bundle_2, timestamp=5.0)

    assert "STEP_02" in state_2.completed_steps
    assert state_2.current_step == "STEP_03"
    assert state_2.next_expected_step == "STEP_04"

    # -------------------------------------------------------------
    # Scenario 3: Astronaut grasps YELLOW_BOX (Wrong object for STEP_03)
    # -------------------------------------------------------------
    yellow_track = Track(
        track_id=3,
        class_name="YELLOW_BOX",
        confidence=0.90,
        bbox=BoundingBox(0.1, 0.4, 0.2, 0.2),
        state=TrackState.VISIBLE,
    )
    p_state_3 = PerceptionState(timestamp=7.5, frame_id=225, source_id="CAM_0", tracks=[yellow_track])

    act_3 = ActivityObservation(
        activity_name="MOVE",
        actor="ASTRONAUT",
        target_object_id="YELLOW_BOX",
        confidence=0.88,
        window=TemporalWindow(start_time=5.5, end_time=7.5),
    )

    bundle_3 = evidence_engine.evaluate(
        activity=act_3,
        tracks=[yellow_track],
        perception_state=p_state_3,
        step=progress_mgr._step_map.get("STEP_03"),
    )

    state_3 = progress_mgr.update(activity=act_3, bundle=bundle_3, timestamp=7.5)

    # Must NOT advance to STEP_04! Current step remains STEP_03
    assert "STEP_03" not in state_3.completed_steps
    assert state_3.current_step == "STEP_03"

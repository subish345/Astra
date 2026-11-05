"""QA6 regressions. Test doubles below are isolated failure inputs, never live evidence."""
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.activity.types import ActivityObservation, TemporalWindow
from core.assurance.engine import TriStateAssuranceEngine
from core.assistance.recovery import ClosedLoopRecoveryManager
from core.assurance.types import AssuranceDecision, DecisionType
from core.camera.interface import FrameData
from core.common.config import AppConfig, get_project_root
from core.evidence.types import EvidenceBundle
from core.mission.events import DeviationReason
from core.perception.pose.mediapipe_adapter import MediaPipePoseEstimator
from core.procedure.progress import ProcedureProgressManager
from core.procedure.validator import load_procedure_file
from core.ui.bridge import BackendEventBridge
from core.ui.worker import MissionPipelineWorker

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def procedure():
    return load_procedure_file(get_project_root() / 'configs/experiments/demo.yaml')

def test_qthread_stop_uses_supported_wait_signature(app):
    worker = MissionPipelineWorker(BackendEventBridge())
    assert worker.stop() is True


def test_next_action_keeps_authoritative_current_step(app, procedure):
    from core.ui.main_window import MissionConsoleWindow
    from core.ui.state import MissionUIState
    window = SimpleNamespace(state=MissionUIState(), console_view=MagicMock())
    MissionConsoleWindow._on_step_progress(window, ProcedureProgressManager(procedure).get_state())
    guidance = window.console_view.step_panel.update_next_action.call_args.args[0]
    assert '01' in guidance
    assert '02' not in guidance


def test_zero_visibility_never_becomes_confident_hand():
    estimator = MediaPipePoseEstimator.__new__(MediaPipePoseEstimator)
    estimator._is_ready = True
    estimator.smoother = None
    landmarks = [SimpleNamespace(x=.5, y=.5, z=0., visibility=0.) for _ in range(33)]
    estimator.detector = SimpleNamespace(detect=lambda image: SimpleNamespace(pose_landmarks=[landmarks]))
    frame = FrameData(1, np.zeros((48, 64, 3), dtype=np.uint8), 1., datetime.now(timezone.utc), 'UNIT_FIXTURE')
    poses = estimator.estimate(frame)
    assert len(poses[0].keypoints) == 33
    assert all(k.confidence == 0. for k in poses[0].keypoints)
    from core.perception.hands.mediapipe_adapter import MediaPipeHandDetector
    assert MediaPipeHandDetector(enable_morphology_fallback=False).detect(frame, poses=poses) == []


@pytest.mark.parametrize('opens', [False, True])
def test_worker_failed_or_empty_camera_never_completes_run(app, monkeypatch, tmp_path, procedure, opens):
    import core.ui.worker as module
    from core.mission.database import DatabaseManager
    root = tmp_path
    monkeypatch.setattr(module, 'get_project_root', lambda: root)
    monkeypatch.setattr(module, 'load_procedure_file', lambda _: procedure)
    cfg = AppConfig(); cfg.streaming.enabled = False; cfg.events.enabled = False
    monkeypatch.setattr(module, 'load_config', lambda: cfg)
    source = MagicMock(); source.start.return_value = opens; source.read.return_value = None; source.is_active = False
    monkeypatch.setattr(module, 'WebcamSource', lambda **_: source)
    worker = MissionPipelineWorker(BackendEventBridge(), session_id='QA_FAILURE')
    worker.run()
    assert worker._is_running is False
    source.stop.assert_called_once()
    db = DatabaseManager(root / 'storage/astra.db')
    with db.get_connection() as conn:
        row = conn.execute("SELECT status FROM experiment_runs WHERE run_id='QA_FAILURE'").fetchone()
    assert row[0] == ('FAILED' if not opens else 'ABORTED')


@pytest.mark.parametrize('name,confidence,metadata', [('IDLE', .95, {}), ('GRASP', .1, {}), ('GRASP', .9, {'occluded': True})])
def test_uncertain_activity_cannot_verify_or_create_wrong_object_deviation(procedure, name, confidence, metadata):
    step = procedure.steps[1]
    activity = ActivityObservation(name, 'actor', 'YELLOW_BOX' if name != 'IDLE' else 'RED_BOX', confidence, TemporalWindow(0., 3.), metadata=metadata)
    bundle = EvidenceBundle(required_satisfied=True, evidence_score=.99)
    decision = TriStateAssuranceEngine().evaluate_step(step, activity, bundle)
    assert decision.is_uncertain


def test_wrong_object_recovery_idle_without_evidence_is_not_verified(procedure):
    manager = ClosedLoopRecoveryManager(); step = procedure.steps[1]
    decision = AssuranceDecision(experiment_id=procedure.id, step_id=step.id, sequence=step.sequence,
        decision=DecisionType.DEVIATION, confidence=.9, deviation_reason=DeviationReason.WRONG_OBJECT)
    manager.handle_decision(decision, step)
    activity = ActivityObservation('IDLE', 'actor', 'YELLOW_BOX', .9, TemporalWindow(0., 2.))
    recovered, _ = manager.observe_corrective_action(activity, EvidenceBundle(), step)
    assert not recovered
    assert not manager.active_context.verified_corrective_action


def test_skipped_step_same_target_is_not_itself_recovery_evidence(procedure):
    manager = ClosedLoopRecoveryManager(); step = procedure.steps[0]
    decision = AssuranceDecision(experiment_id=procedure.id, step_id=step.id, sequence=step.sequence,
        decision=DecisionType.DEVIATION, confidence=.9, deviation_reason=DeviationReason.SKIPPED_STEP)
    manager.handle_decision(decision, step)
    activity = ActivityObservation('GRASP', 'actor', 'RED_BOX', .9, TemporalWindow(0., 2.))
    assert manager.observe_corrective_action(activity, EvidenceBundle(), step)[0] is False


def test_live_activity_label_does_not_invent_missing_object(procedure):
    from core.evidence.engine import MultimodalEvidenceEngine
    from core.perception.types import PerceptionState
    activity = ActivityObservation('GRASP', 'actor', 'RED_BOX', .95, TemporalWindow(0., 3.))
    state = PerceptionState(timestamp=3., frame_id=100, source_id='UNIT_FIXTURE')
    bundle = MultimodalEvidenceEngine().evaluate(activity, interactions=[], perception_state=state, step=procedure.steps[1])
    assert not bundle.check_requirement('OBJECT_DETECTED')
    assert not bundle.required_satisfied


def test_other_object_contact_cannot_satisfy_target(procedure):
    from core.evidence.engine import MultimodalEvidenceEngine
    from core.interaction.types import InteractionEvent, InteractionState
    from core.perception.types import HandType, PerceptionState
    activity = ActivityObservation('GRASP', 'actor', 'RED_BOX', .95, TemporalWindow(0., 3.))
    interaction = InteractionEvent(target_object_id='YELLOW_BOX', target_track_id=2, hand_type=HandType.RIGHT,
        state=InteractionState.CONTACT, distance=.01, confidence=.95, timestamp=3.)
    state = PerceptionState(timestamp=3., frame_id=100, source_id='UNIT_FIXTURE')
    bundle = MultimodalEvidenceEngine().evaluate(activity, interactions=[interaction], perception_state=state, step=procedure.steps[1])
    assert not bundle.check_requirement('HAND_OBJECT_CONTACT')


@pytest.mark.parametrize('actions', [['MOVE'], ['PLACE'], ['MOVE', 'LIFT', 'APPROACH_DESTINATION', 'PLACE']])
def test_placement_requires_complete_ordered_action_sequence(procedure, actions):
    from core.procedure.types import StepCandidate, StepMatchStatus
    from core.procedure.evaluator import StepEvaluator
    candidate = StepCandidate(step_id='STEP_03', activity_type=actions[-1], object_id='RED_BOX',
        match_score=.99, timestamp_start=0., timestamp_end=5., match_details={'primitives': actions})
    bundle = EvidenceBundle(required_satisfied=True, evidence_score=.99)
    assert StepEvaluator().evaluate_step(candidate, bundle, procedure.steps[2]).status != StepMatchStatus.VERIFIED


def test_future_candidate_cannot_skip_authoritative_step(procedure):
    progress = ProcedureProgressManager(procedure)
    act = ActivityObservation('GRASP', 'actor', 'RED_BOX', .99, TemporalWindow(0., 5.))
    state = progress.update(act, EvidenceBundle(required_satisfied=True, evidence_score=.99))
    assert state.current_step == 'STEP_01'
    assert state.completed_steps == []


def test_console_pose_and_main_box_indicators_match_observations(app):
    from core.ui.panels.video_panel import VideoPanel
    from core.perception.types import PerceptionState, PoseObservation, Track, BoundingBox
    panel = VideoPanel()
    state = PerceptionState(timestamp=1., frame_id=1, source_id='UNIT_FIXTURE',
        poses=[PoseObservation(person_id=1, keypoints=[], confidence=.9)],
        tracks=[Track(1, 'RED_BOX', BoundingBox(1, 1, 5, 5), .9)])
    panel.update_frame(np.zeros((10, 10, 3), dtype=np.uint8), state)
    assert '✓' in panel.lbl_ent_astro.text()
    assert '✓' in panel.lbl_ent_red.text()
    assert '✓' not in panel.lbl_ent_main.text()
    panel.close()


def test_mission_console_default_hides_developer_hud(app):
    worker = MissionPipelineWorker(BackendEventBridge())
    assert not worker.overlay_config.show_hud
    assert not worker.overlay_config.show_confidence
    assert not worker.overlay_config.show_laser_guides


def test_empty_live_scene_has_no_pose_stability_or_destination_evidence(procedure):
    from core.evidence.engine import MultimodalEvidenceEngine
    from core.perception.types import PerceptionState
    state=PerceptionState(timestamp=1.,frame_id=1,source_id='UNIT_FIXTURE')
    bundle=MultimodalEvidenceEngine().evaluate(perception_state=state,step=procedure.steps[0])
    for name in ['POSE_CONSISTENCY','OBJECT_STABILIZED','DESTINATION_MATCH']:
        assert not bundle.check_requirement(name)


@pytest.mark.parametrize('width,height', [(640,480),(1280,720)])
def test_pixel_coordinates_are_normalized_for_evidence(procedure,width,height):
    from core.evidence.engine import MultimodalEvidenceEngine
    from core.perception.types import PerceptionState,PoseObservation,Track,BoundingBox
    person=PoseObservation(1,[],.95,bbox=BoundingBox(.2*width,.3*height,.4*width,.7*height))
    track=Track(1,'MAIN_BOX',BoundingBox(.4*width,.4*height,.5*width,.6*height),.95)
    state=PerceptionState(timestamp=3.,frame_id=90,source_id='UNIT_FIXTURE',frame_width=width,frame_height=height,persons=[person],poses=[person],tracks=[track])
    activity=ActivityObservation('APPROACH','actor','MAIN_BOX',.95,TemporalWindow(0.,3.))
    bundle=MultimodalEvidenceEngine().evaluate(activity,perception_state=state,step=procedure.steps[0])
    assert bundle.check_requirement('SPATIAL_PROXIMITY')
    assert bundle.items['SPATIAL_PROXIMITY'].details['normalized_distance']==pytest.approx(.15)

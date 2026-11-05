"""Exercise real Qt lifecycle controls without opening a camera or writing sessions."""
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from core.common.config import get_project_root
from core.ui.main_window import MissionConsoleWindow


@pytest.fixture
def setup_window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    workers = []

    def factory(**kwargs):
        worker = MagicMock()
        worker.isRunning.return_value = False
        worker.start.side_effect = lambda: setattr(worker.isRunning, "return_value", True)
        def stop():
            worker.isRunning.return_value = False
            return True
        worker.stop.side_effect = stop
        worker.session_id = kwargs["session_id"]
        worker.camera_source = kwargs["camera_source"]
        workers.append(worker)
        return worker

    monkeypatch.setattr("core.ui.main_window.MissionPipelineWorker", factory)
    window = MissionConsoleWindow(
        procedure_path=str(get_project_root() / "configs/experiments/always_observe.yaml"),
        voice_manager=MagicMock(),
    )
    yield app, window, workers
    window.close()


def test_auto_start_no_duplicate_and_unique_restart(setup_window):
    app, window, workers = setup_window
    app.processEvents()
    assert len(workers) == 1
    first = window.session_id
    window.start_mission()
    assert len(workers) == 1
    window.stop_mission()
    window.start_mission()
    assert len(workers) == 2
    assert window.session_id != first


def test_stop_cancels_pending_auto_start(setup_window):
    app, window, workers = setup_window
    window.stop_mission()
    app.processEvents()
    assert not workers


def test_live_pause_does_not_stop_camera(setup_window):
    app, window, workers = setup_window
    app.processEvents()
    window.pause_mission()
    workers[0].pause.assert_not_called()
    assert "STOP" in window.status_bar.currentMessage()


def test_live_has_no_default_procedure_instructions(setup_window):
    _, window, _ = setup_window
    window._on_step_progress(MagicMock())
    panel = window.console_view.step_panel
    assert panel.lbl_step_num.text() == "LIVE OBSERVE"
    assert "No procedure" in panel.lbl_expected.text()


def test_live_hides_demo_only_panels(setup_window):
    _, window, _ = setup_window
    assert window.console_view.progress_panel.isHidden()
    assert window.console_view.status_panel.isHidden()
    assert window.console_view.evidence_panel.isHidden()
    assert window.console_view.video_panel.live_observe


def test_apply_camera_source_stops_old_worker_first(setup_window):
    app, window, workers = setup_window
    app.processEvents()
    window.settings_view.txt_source.setText("1")
    window.settings_view.btn_apply_source.click()
    assert len(workers) == 2
    workers[0].stop.assert_called_once()
    assert workers[1].camera_source == "1"


def test_invalid_video_keeps_current_session(setup_window):
    app, window, workers = setup_window
    app.processEvents()
    window.settings_view.txt_source.setText("/definitely-missing/video.webm")
    window.apply_camera_settings()
    assert len(workers) == 1
    workers[0].stop.assert_not_called()
    assert "not found" in window.settings_view.lbl_source_status.text()


def test_camera_failure_is_not_shown_online(setup_window):
    _, window, _ = setup_window
    window._on_session_status("CAMERA_FAILURE")
    assert window.console_view.video_panel.lbl_cam_status.text() == "CAMERA_FAILURE"
    assert not window.session_bar.btn_start.isEnabled()
    assert window.session_bar.btn_stop.isEnabled()


def test_general_object_summary_uses_current_detections(setup_window):
    import numpy as np
    from core.perception.types import PerceptionState, Detection, BoundingBox
    _, window, _ = setup_window
    panel = window.console_view.video_panel
    state = PerceptionState(1, 1, "test", objects=[Detection("cell phone", 0.91, BoundingBox(2, 2, 20, 20))])
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    panel.update_frame(frame, state)
    assert "cell phone" in panel.lbl_live_objects.text()
    state.objects = []
    panel.update_frame(frame, state)
    assert "cell phone" not in panel.lbl_live_objects.text()

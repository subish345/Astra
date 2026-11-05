# ==============================================================================
# ORBITA Video Recording & Playback Speed Unit Tests
# ==============================================================================
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from core.mission.database import DatabaseManager
from core.mission.recording import UnifiedRecordingManager


def test_recording_realtime_pacing_and_clarity():
    """Verify that video recorded from a slower processing loop (~15 FPS) encodes

    with timestamp pacing to produce an exact 1.0x real-time speed 30 FPS MP4 file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        rec_mgr = UnifiedRecordingManager(base_dir=tmpdir)
        db_path = Path(tmpdir) / "test.db"
        db = DatabaseManager(db_path)
        db.initialize()

        run_id = "TEST_PACING_001"
        target_fps = 30
        res = (1280, 720)

        out_path = rec_mgr.start_recording(run_id=run_id, fps=target_fps, resolution=res)
        assert out_path.exists()
        assert rec_mgr.is_recording

        # Simulate 15 FPS feed over 1.0 second elapsed monotonic time
        start_mono = 1000.0
        frame_interval = 1.0 / 15.0  # ~0.0667s per cycle (slow AI processing)
        total_real_seconds = 1.0

        num_input_frames = int(total_real_seconds / frame_interval)
        for i in range(num_input_frames):
            ts = start_mono + (i * frame_interval)
            # Create a clear 1280x720 test frame
            frame = np.full((720, 1280, 3), fill_value=(i * 15) % 255, dtype=np.uint8)
            cv2.putText(frame, f"Frame {i}", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
            pushed = rec_mgr.record_frame(frame, timestamp=ts)
            assert pushed

        # Push one final frame at t=1.0s to close the 1-second interval
        final_ts = start_mono + total_real_seconds
        rec_mgr.record_frame(np.zeros((720, 1280, 3), dtype=np.uint8), timestamp=final_ts)

        # Finalize recording and save to DB
        saved_path = rec_mgr.stop_recording(db_manager=db)
        assert saved_path is not None
        assert saved_path.exists()
        assert not rec_mgr.is_recording

        # Verify video properties using OpenCV VideoCapture
        cap = cv2.VideoCapture(str(saved_path))
        assert cap.isOpened()

        actual_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Resolution clarity check
        assert actual_w == 1280
        assert actual_h == 720
        assert actual_fps == 30.0

        # Pacing speed check:
        # 1.0 second of real time at 30 FPS must produce ~30-31 frames (duration ~ 1.0s), NOT 15 frames (0.5s)!
        duration = actual_frames / actual_fps
        assert 29 <= actual_frames <= 32, f"Expected ~30 frames for 1.0s real time, got {actual_frames}"
        assert 0.95 <= duration <= 1.10, f"Expected ~1.0s normal-speed duration, got {duration:.2f}s"

        # Verify database record
        segments = db.get_video_segments()
        assert len(segments) == 1
        seg = segments[0]
        assert seg["run_id"] == run_id
        assert seg["frame_count"] == actual_frames
        assert seg["fps"] == 30.0
        assert 0.95 <= seg["duration_sec"] <= 1.10
        assert seg["file_path"] == str(saved_path)

        db.close()


def test_recording_view_speed_controls(qtbot=None):
    """Verify RecordingsView playback speed adjustments and UI controls."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from core.ui.views.recordings_view import RecordingsView

    view = RecordingsView()
    assert view.playback_speed == 1.0
    assert view.cmb_speed.currentText() == "1.0x (Normal)"

    # Change to Slow (0.5x)
    view.cmb_speed.setCurrentIndex(1)
    assert view.playback_speed == 0.5

    # Change to Quarter (0.25x)
    view.cmb_speed.setCurrentIndex(2)
    assert view.playback_speed == 0.25

    # Change to Fast (1.5x)
    view.cmb_speed.setCurrentIndex(3)
    assert view.playback_speed == 1.5

    # Change back to Normal (1.0x)
    view.cmb_speed.setCurrentIndex(0)
    assert view.playback_speed == 1.0

    view.close()


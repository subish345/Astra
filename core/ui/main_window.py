# ==============================================================================
# Pramman Mission Console Main Window
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Main Qt application shell for the Pramman Mission Console."""

from __future__ import annotations

import time
from uuid import uuid4
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from core.ui.bridge import BackendEventBridge
from core.ui.panels.session_bar import SessionBar
from core.ui.state import EvidenceItemState, MissionUIState, TimelineEventState
from core.ui.theme import Colors, MAIN_STYLESHEET
from core.ui.views.console_view import ConsoleView
from core.ui.views.evidence_view import EvidenceView
from core.ui.views.health_view import HealthView
from core.ui.views.recordings_view import RecordingsView
from core.ui.views.settings_view import SettingsView
from core.ui.views.timeline_view import TimelineView
from core.ui.worker import MissionPipelineWorker
from core.voice.manager import AudioQueueManager
from core.voice.interface import AudioPriority


class MissionConsoleWindow(QMainWindow):
    """Main application window for the Pramman Mission Console."""

    def __init__(
        self,
        procedure_path: str = "configs/experiments/demo.yaml",
        camera_source: str = "0",
        camera_profile: str = "view_left",
        session_id: str = "SESSION_001",
        voice_manager: Optional[AudioQueueManager] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ORBITA — Mission Console [SIH26174]")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 680)
        self.setStyleSheet(MAIN_STYLESHEET)

        self.procedure_path = procedure_path
        self._mode_cache = None
        self.camera_source = camera_source
        self.camera_profile = camera_profile
        self.session_id = session_id
        self._session_prefix = session_id
        self.voice_manager = voice_manager or AudioQueueManager()

        self.state = MissionUIState()
        self.mirror_camera: bool = False
        self.bridge = BackendEventBridge(self)
        self.worker: Optional[MissionPipelineWorker] = None
        self._auto_start_timer = QTimer(self)
        self._auto_start_timer.setSingleShot(True)
        self._auto_start_timer.timeout.connect(self.start_mission)

        self._init_ui()
        # Match the selector to the actual launch procedure, not alphabetical order.
        from core.common.config import get_project_root
        selected = Path(self.procedure_path)
        if not selected.is_absolute():
            selected = get_project_root() / selected
        combo = self.session_bar.cmb_exp
        combo.blockSignals(True)
        for index in range(combo.count()):
            if Path(combo.itemData(index)).resolve() == selected.resolve():
                combo.setCurrentIndex(index)
                break
        combo.blockSignals(False)
        self._connect_signals()
        self._setup_shortcuts()
        self._sync_mode_panels()
        if self._live_observe_selected():
            self._auto_start_timer.start(0)

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 6, 8, 6)
        root_layout.setSpacing(6)

        # Top Session Header Bar
        self.session_bar = SessionBar(
            on_start=self.start_mission,
            on_pause=self.pause_mission,
            on_stop=self.stop_mission,
            on_upload_video=self.upload_and_verify_video,
            on_toggle_record=self.toggle_recording,
            on_toggle_mirror=self.toggle_camera_mirror,
            on_experiment_changed=self._on_experiment_changed,
            parent=self,
        )
        self.session_bar.set_camera_profile(self.camera_profile)
        self.session_bar.set_session_state("READY", self.session_id)
        root_layout.addWidget(self.session_bar)

        # Body Layout: Sidebar Navigation + Main Stack
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(6)

        # Sidebar Navigation Frame
        nav_frame = QFrame()
        nav_frame.setObjectName("PanelFrame")
        nav_frame.setFixedWidth(130)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(4, 8, 4, 8)
        nav_layout.setSpacing(4)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("MISSION", 0),
            ("RECORDINGS", 1),
            ("EVIDENCE", 2),
            ("TIMELINE", 3),
            ("HEALTH", 4),
            ("SETTINGS", 5),
        ]

        for label, idx in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, i=idx: self.stack.setCurrentIndex(i))
            self.nav_group.addButton(btn, idx)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()

        # Fullscreen Toggle button
        self.btn_fs = QPushButton("⛶ Fullscreen")
        self.btn_fs.setObjectName("NavButton")
        self.btn_fs.clicked.connect(self.toggle_fullscreen)
        nav_layout.addWidget(self.btn_fs)

        body_layout.addWidget(nav_frame)

        # Stacked Views
        self.stack = QStackedWidget(self)

        self.console_view = ConsoleView(self)
        if hasattr(self.console_view, "video_panel") and hasattr(self.console_view.video_panel, "btn_mirror"):
            self.console_view.video_panel.btn_mirror.toggled.connect(self.toggle_camera_mirror)
        self.stack.addWidget(self.console_view)  # 0

        self.recordings_view = RecordingsView(on_verify_video=self.verify_selected_video, parent=self)
        self.stack.addWidget(self.recordings_view)  # 1

        self.evidence_view = EvidenceView(self)
        self.stack.addWidget(self.evidence_view)  # 2

        self.timeline_view = TimelineView(self)
        self.stack.addWidget(self.timeline_view)  # 3

        self.health_view = HealthView(self)
        self.stack.addWidget(self.health_view)  # 4

        self.settings_view = SettingsView(on_test_voice=self.test_voice_guidance, parent=self)
        self.settings_view.txt_source.setText(self.camera_source)
        self.settings_view.cmb_profile.setCurrentIndex({"view_left": 0, "view_right": 1, "view_center": 2}.get(self.camera_profile.lower(), 0))
        self.settings_view.btn_apply_source.clicked.connect(self.apply_camera_settings)
        self.stack.addWidget(self.settings_view)  # 5

        body_layout.addWidget(self.stack, stretch=1)
        root_layout.addLayout(body_layout, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet(f"background-color: {Colors.BG_PANEL}; color: {Colors.TEXT_MUTED}; font-size: 11px;")
        self.status_bar.showMessage("ORBITA v1.0.0 (Mission Console) | Air-Gapped Local Operation | Optical Source Ready")
        self.setStatusBar(self.status_bar)

    def _on_experiment_changed(self, procedure_path: str) -> None:
        """Select the procedure used by the next mission run."""
        if self.worker and self.worker.isRunning():
            return
        self.procedure_path = procedure_path
        self._auto_start_timer.stop()
        self.status_bar.showMessage(f"Selected experiment: {Path(procedure_path).stem}")
        self._sync_mode_panels()
        if self._live_observe_selected():
            self._auto_start_timer.start(0)

    def _live_observe_selected(self) -> bool:
        cached = self._mode_cache
        if cached is not None and cached[0] == str(self.procedure_path):
            return cached[1]
        from core.common.config import get_project_root
        from core.procedure.validator import load_procedure_file
        path = Path(self.procedure_path)
        if not path.is_absolute():
            path = get_project_root() / path
        try:
            result = bool(load_procedure_file(path).continuous_observation)
            self._mode_cache = (str(self.procedure_path), result)
            return result
        except Exception:
            return False

    def _connect_signals(self) -> None:
        """Connect bridge signals to UI update methods."""
        self.bridge.sig_frame_ready.connect(self._on_frame_ready)
        self.bridge.sig_step_progress.connect(self._on_step_progress)
        self.bridge.sig_assurance_decision.connect(self._on_assurance_decision)
        self.bridge.sig_evidence_bundle.connect(self._on_evidence_bundle)
        self.bridge.sig_deviation.connect(self._on_deviation)
        self.bridge.sig_recovery.connect(self._on_recovery)
        self.bridge.sig_voice.connect(self._on_voice)
        self.bridge.sig_health.connect(self._on_health)
        self.bridge.sig_timeline_event.connect(self._on_timeline_event)
        self.bridge.sig_session_status.connect(self._on_session_status)
        self.bridge.sig_recording_status.connect(self._on_recording_status)

    def _sync_mode_panels(self):
        live = self._live_observe_selected()
        for panel in (self.console_view.progress_panel, self.console_view.status_panel, self.console_view.evidence_panel):
            panel.setVisible(not live)
        self.console_view.video_panel.set_live_observe(live)
        if live:
            self._on_step_progress(None)
            self.console_view.step_panel.lbl_status_badge.setText(self.state.session.status)

    def apply_camera_settings(self):
        from core.common.config import get_project_root
        source = self.settings_view.txt_source.text().strip()
        if not source:
            self.settings_view.lbl_source_status.setText("Enter a camera index or choose a video file.")
            return
        if not source.isdigit():
            path = Path(source).expanduser()
            if not path.is_absolute():
                path = get_project_root() / path
            if not path.is_file():
                self.settings_view.lbl_source_status.setText(f"Video file not found: {path}. Current session unchanged.")
                return
            source = str(path)
        self.stop_mission()
        if self.worker is not None:
            self.settings_view.lbl_source_status.setText("Previous capture is still stopping. Wait, then apply again.")
            return
        self.camera_source = source
        self.camera_profile = ("view_left", "view_right", "view_center")[self.settings_view.cmb_profile.currentIndex()]
        self.session_bar.set_camera_profile(self.camera_profile)
        self.settings_view.lbl_source_status.setText(f"Opening {source}…")
        self.start_mission()

    def _setup_shortcuts(self) -> None:
        """Keyboard shortcuts."""
        fs_shortcut = QShortcut(QKeySequence("F11"), self)
        fs_shortcut.activated.connect(self.toggle_fullscreen)

        esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        esc_shortcut.activated.connect(self._on_escape)

    def toggle_fullscreen(self) -> None:
        """Toggle between windowed and fullscreen display."""
        if self.isFullScreen():
            self.showNormal()
            self.btn_fs.setText("⛶ Fullscreen")
        else:
            self.showFullScreen()
            self.btn_fs.setText("❐ Exit Fullscreen")

    def _on_escape(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.btn_fs.setText("⛶ Fullscreen")

    # =========================================================================
    # Mission Lifecycle Actions
    # =========================================================================

    def upload_and_verify_video(self) -> None:
        """Prompt operator to select an experiment video file and immediately verify movements and steps."""
        from core.common.config import get_project_root

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Upload / Select Experiment Video File",
            str(get_project_root()),
            "Video Files (*.mp4 *.avi *.mkv *.webm *.mov);;All Files (*)",
        )
        if not file_path:
            return

        vid_path = Path(file_path).resolve()
        if not vid_path.is_file():
            self._on_timeline_event("SYSTEM", "Invalid File", f"File not found: {vid_path}", "DANGER")
            return

        self.stop_mission()
        self.camera_source = str(vid_path)
        self.settings_view.txt_source.setText(str(vid_path))
        self.session_bar.set_mode("REPLAY")
        self.session_bar.lbl_sys_status.setText("🎥 VIDEO VERIFY")
        self._on_timeline_event("SYSTEM", "Video Uploaded", f"Analyzing movement & step accuracy: {vid_path.name}", "INFO")

        # Automatically start verification on the uploaded video
        self.start_mission()

    def verify_selected_video(self, video_path: str) -> None:
        """Load a recorded video segment from the archive and replay for step/movement verification."""
        vpath = Path(video_path).resolve()
        if not vpath.exists():
            return
        self.stop_mission()
        self.camera_source = str(vpath)
        self.settings_view.txt_source.setText(str(vpath))
        self.session_bar.set_mode("REPLAY")
        self.session_bar.lbl_sys_status.setText("🎥 REPLAY / VERIFY")
        self._on_timeline_event(
            "RECORDINGS",
            "Loaded Recording",
            f"Replaying {vpath.name} for step verification.",
            "INFO",
        )
        self.stack.setCurrentIndex(0)
        btn_mission = self.nav_group.button(0)
        if btn_mission:
            btn_mission.setChecked(True)
        self.start_mission()

    def toggle_camera_mirror(self, enabled: Optional[bool] = None) -> None:
        """Toggle camera horizontal mirroring (mirror view)."""
        if enabled is None:
            self.mirror_camera = not getattr(self, "mirror_camera", False)
        else:
            self.mirror_camera = bool(enabled)

        # Sync session bar button
        if hasattr(self, "session_bar") and hasattr(self.session_bar, "btn_mirror"):
            self.session_bar.btn_mirror.blockSignals(True)
            self.session_bar.btn_mirror.setChecked(self.mirror_camera)
            self.session_bar.btn_mirror.blockSignals(False)

        # Sync video panel button
        if hasattr(self, "console_view") and hasattr(self.console_view, "video_panel"):
            vp = self.console_view.video_panel
            if hasattr(vp, "btn_mirror"):
                vp.btn_mirror.blockSignals(True)
                vp.btn_mirror.setChecked(self.mirror_camera)
                vp.btn_mirror.blockSignals(False)

        # Apply to active worker immediately
        if self.worker:
            self.worker.mirror_camera = self.mirror_camera

        status_text = "MIRRORED (SELFIE)" if self.mirror_camera else "STANDARD"
        self._on_timeline_event("CAMERA", f"Camera View: {status_text}", f"Camera mirroring {'enabled' if self.mirror_camera else 'disabled'}", "INFO")

    def toggle_recording(self) -> None:
        """Toggle manual video recording for the active session."""
        if self.worker is not None and self.worker.isRunning():
            if self.worker.recording_manager.is_recording:
                self.worker.stop_manual_recording()
            else:
                self.worker.start_manual_recording()
        else:
            self._on_timeline_event(
                "SYSTEM",
                "Recording Notice",
                "Start a mission run first to begin recording.",
                "WARNING",
            )

    def start_mission(self) -> None:
        """Launch the background pipeline worker."""
        self._auto_start_timer.stop()
        if self.worker is not None and self.worker.isRunning():
            return

        self._mode_cache = None
        self._sync_mode_panels()
        self.session_id = f"{self._session_prefix}-{uuid4().hex}"
        self.worker = MissionPipelineWorker(
            bridge=self.bridge,
            procedure_path=self.procedure_path,
            camera_source=self.camera_source,
            camera_profile=self.camera_profile,
            session_id=self.session_id,
            voice_manager=self.voice_manager,
            parent=self,
        )
        self.worker.mirror_camera = getattr(self, "mirror_camera", False)
        self.worker.start()
        self._on_session_status("INITIALIZING")

    def pause_mission(self) -> None:
        """Pause or resume the pipeline worker."""
        if self._live_observe_selected():
            self.status_bar.showMessage("Live Observe keeps the camera active. Use STOP to end observation.")
            return
        if self.worker:
            self.worker.pause()
            self.session_bar.set_session_state("PAUSED", self.session_id)

    def stop_mission(self) -> None:
        """Stop background execution."""
        self._auto_start_timer.stop()
        if self.worker:
            if not self.worker.stop():
                self._on_session_status("STOPPING")
                return
            self.worker = None
        if not self.camera_source.isdigit():
            self.camera_source = "0"
            self.settings_view.txt_source.setText("0")
        self.session_bar.set_mode("FULL_REAL")
        self.session_bar.lbl_sys_status.setText("🟢 SYSTEM: NORMAL")
        self._on_session_status("READY")

    def test_voice_guidance(self) -> None:
        """Test audio guidance utterance."""
        self.voice_manager.speak("Testing ORBITA audio guidance channel. Systems nominal.", priority=AudioPriority.INFO)

    # =========================================================================
    # Backend Bridge Event Handlers (Executed on Main Qt UI Thread)
    # =========================================================================

    def _on_frame_ready(self, frame_np, perception_state) -> None:
        panel = self.console_view.video_panel
        if self.worker:
            config = self.worker.overlay_config
            config.show_pose = panel.show_pose
            config.show_hands = panel.show_hands
            config.show_boxes = panel.show_objects
            config.show_tracks = panel.show_tracking
            config.show_lost_tracks = panel.show_debug
            config.show_interactions = panel.show_interaction
            config.show_hud = panel.show_debug
            config.show_confidence = panel.show_debug
            config.show_laser_guides = panel.show_debug
        self.console_view.video_panel.update_frame(frame_np, perception_state)
        self.console_view.health_panel.set_subsystem_status("Camera", "ONLINE")
        self.console_view.health_panel.set_subsystem_status("Perception", "ACTIVE")

    def _on_step_progress(self, proc_state) -> None:
        if self._live_observe_selected():
            panel = self.console_view.step_panel
            panel.lbl_step_num.setText("LIVE OBSERVE")
            panel.lbl_step_title.setText("Continuous person and hand observation")
            panel.lbl_expected.setText("No procedure sequence required")
            panel.lbl_status_badge.setText("OBSERVING")
            panel.update_next_action("Move naturally; keep your hands and objects visible. STOP ends observation.")
            return
        completed = proc_state.completed_steps if hasattr(proc_state, "completed_steps") else []
        curr_step = proc_state.current_step if hasattr(proc_state, "current_step") else None
        next_step = proc_state.next_expected_step if hasattr(proc_state, "next_expected_step") else None
        if hasattr(proc_state, "procedure_status"):
            status_name = proc_state.procedure_status.value if hasattr(proc_state.procedure_status, "value") else str(proc_state.procedure_status)
        elif hasattr(proc_state, "status"):
            status_name = proc_state.status.value if hasattr(proc_state.status, "value") else str(proc_state.status)
        else:
            status_name = "MONITORING"

        self.state.apply_step_progress(curr_step, next_step, completed, status_name)
        self.console_view.progress_panel.update_steps(self.state.step_statuses, curr_step)

        # Update step panel
        step_idx = len(completed) + 1
        if curr_step:
            self.console_view.step_panel.update_step(
                step_number=step_idx,
                total_steps=self.state.experiment.total_steps,
                step_name=curr_step.replace("_", " ").title(),
                expected_action=f"VERIFYING {curr_step}",
                status=self.state.step_statuses.get(curr_step, "IN_PROGRESS"),
            )
        if curr_step:
            self.console_view.step_panel.update_next_action(f"Complete {curr_step.replace('_', ' ').title()}")
        elif status_name == "COMPLETED":
            self.console_view.step_panel.update_next_action("EXPERIMENT COMPLETE", is_completed=True)

    def _on_assurance_decision(self, decision, step_def) -> None:
        if hasattr(decision, "decision"):
            dec_type = decision.decision.value if hasattr(decision.decision, "value") else str(decision.decision)
        elif hasattr(decision, "decision_type"):
            dec_type = decision.decision_type.value if hasattr(decision.decision_type, "value") else str(decision.decision_type)
        else:
            dec_type = str(decision)

        conf = decision.confidence if hasattr(decision, "confidence") else 0.0
        reasons = decision.reasons if hasattr(decision, "reasons") else []
        step_id = step_def.id if step_def else None

        self.state.apply_assurance_decision(dec_type, conf, reasons, step_id=step_id)

        if dec_type == "VERIFIED":
            step_title = step_def.name if step_def else "Step"
            self.console_view.status_panel.show_verified(step_title, conf, reasons)
        elif dec_type == "UNCERTAIN":
            self.console_view.status_panel.show_uncertain("; ".join(reasons) if reasons else "Partial occlusion detected.")

    def _on_evidence_bundle(self, bundle) -> None:
        items = []
        if hasattr(bundle, "items"):
            for factor, item in bundle.items.items():
                score_val = getattr(item, "confidence", getattr(item, "score", 0.0))
                sat_val = getattr(item, "verified", getattr(item, "is_satisfied", False))
                det_str = str(item.details) if getattr(item, "details", None) else ""
                frame_idx = getattr(item, "end_frame", getattr(item, "start_frame", getattr(item, "source_frame", 0))) or 0
                items.append(
                    EvidenceItemState(
                        evidence_type=str(factor),
                        score=float(score_val),
                        is_satisfied=bool(sat_val),
                        details=det_str,
                        timestamp=time.time(),
                        source_frame=int(frame_idx),
                    )
                )
        score = getattr(bundle, "evidence_score", getattr(bundle, "score", 0.0))
        self.console_view.evidence_panel.update_evidence(items, bundle_score=score)

    def _on_deviation(self, decision, step_def) -> None:
        if hasattr(decision, "deviation_reason") and decision.deviation_reason:
            dev_type = decision.deviation_reason.value if hasattr(decision.deviation_reason, "value") else str(decision.deviation_reason)
        elif hasattr(decision, "deviation_type") and decision.deviation_type:
            dev_type = decision.deviation_type.value if hasattr(decision.deviation_type, "value") else str(decision.deviation_type)
        else:
            dev_type = "PROCEDURE_DEVIATION"

        if step_def and hasattr(step_def, "expected_objects") and step_def.expected_objects:
            exp_obj = ", ".join(step_def.expected_objects)
        elif step_def and hasattr(step_def, "target_object"):
            exp_obj = step_def.target_object
        else:
            exp_obj = "EXPECTED OBJECT"

        det_obj = getattr(decision, "target_object", None) or "UNKNOWN OBJECT"
        reasons = "; ".join(decision.reasons) if hasattr(decision, "reasons") and decision.reasons else "Step requirements not satisfied."
        rec_guidance = f"Return {det_obj} and acquire {exp_obj} to continue {step_def.id if step_def else 'procedure'}."

        self.state.apply_deviation(dev_type, exp_obj, det_obj, reasons, rec_guidance)
        self.console_view.status_panel.show_deviation(dev_type, exp_obj, det_obj, reasons, rec_guidance)

    def _on_recovery(self, context) -> None:
        state_name = context.state.value if hasattr(context.state, "value") else str(context.state)
        instruction = getattr(context, "recommendation", None) or getattr(context, "recovery_action", "Awaiting corrective action.")
        verified = bool(getattr(context, "verified_corrective_action", False) or state_name in ("RESUMED", "RECOVERY_VERIFIED", "RESUME"))
        self.state.apply_recovery(state_name, instruction, verified=verified)
        self.console_view.status_panel.show_recovery(state_name, instruction, verified=verified)

    def _on_voice(self, text: str, prio_name: str) -> None:
        self.status_bar.showMessage(f"AUDIO GUIDANCE [{prio_name}]: \"{text}\"", 5000)

    def _on_health(self, data: dict) -> None:
        fps = data.get("fps", 30.0)
        lat = data.get("latency_ms", 12.0)
        cpu = data.get("cpu_pct", 18.0)
        ram = data.get("ram_mb", 420.0)
        self.console_view.health_panel.update_telemetry(fps, lat, cpu, ram)

    def _on_timeline_event(self, ev_type: str, title: str, desc: str, severity: str) -> None:
        ev = self.state.add_timeline_event(ev_type, title, desc, severity)
        self.console_view.timeline_panel.add_event(ev)
        self.timeline_view.add_event(ev)

    def _on_session_status(self, status: str) -> None:
        self.state.session.status = status
        self.session_bar.set_session_state(status, self.session_id)
        busy = status in {"INITIALIZING", "RUNNING", "CAMERA_FAILURE", "STOPPING"}
        self.session_bar.cmb_exp.setEnabled(not busy)
        self.session_bar.btn_start.setEnabled(not busy)
        self.session_bar.btn_stop.setEnabled(busy or status in ("PAUSED", "COMPLETED"))
        self.session_bar.btn_pause.setEnabled(status == "RUNNING" and not self._live_observe_selected())
        self.settings_view.lbl_source_status.setText(f"Source {self.camera_source}: {status}. See timeline for errors.")
        if status != "RUNNING":
            self.console_view.video_panel.set_source_status(status)
        health = self.console_view.health_panel
        health.lbl_core_state.setText(f"SESSION: {status}")
        live = self._live_observe_selected()
        for name in ("Camera", "Perception", "Procedure", "Assurance"):
            value = "NOT USED" if live and name in {"Procedure", "Assurance"} else status
            health.set_subsystem_status(name, value)
        if status != "RUNNING":
            health.lbl_fps.setText("FPS: —")
            health.lbl_lat.setText("LATENCY: —")
        if live:
            self.console_view.step_panel.lbl_status_badge.setText(status)
        if status in ("COMPLETED", "FAILED"):
            if self.worker is not None and not self.worker.isRunning():
                try:
                    self.worker.wait(100)
                except Exception:
                    pass
                self.worker = None

    def _on_recording_status(self, is_rec: bool, file_path: str) -> None:
        """Handle recording status updates from background worker."""
        self.session_bar.set_recording_state(is_rec, file_path)
        if not is_rec and hasattr(self, "recordings_view"):
            self.recordings_view.refresh_recordings()

    def closeEvent(self, event) -> None:
        """Clean shutdown upon window close."""
        self.stop_mission()
        if self.worker is not None and self.worker.isRunning():
            event.ignore()
            return
        if self.voice_manager:
            self.voice_manager.shutdown()
        event.accept()

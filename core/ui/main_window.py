# ==============================================================================
# ASTRA-EA Mission Console Main Window
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Main Qt application shell for the ASTRA-EA Mission Console."""

from __future__ import annotations

import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
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
from core.ui.views.settings_view import SettingsView
from core.ui.views.timeline_view import TimelineView
from core.ui.worker import MissionPipelineWorker
from core.voice.manager import AudioQueueManager
from core.voice.interface import AudioPriority


class MissionConsoleWindow(QMainWindow):
    """Main application window for the ASTRA-EA Mission Console."""

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
        self.setWindowTitle("ASTRA-EA — Mission Console [SIH26174]")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 680)
        self.setStyleSheet(MAIN_STYLESHEET)

        self.procedure_path = procedure_path
        self.camera_source = camera_source
        self.camera_profile = camera_profile
        self.session_id = session_id
        self.voice_manager = voice_manager or AudioQueueManager()

        self.state = MissionUIState()
        self.bridge = BackendEventBridge(self)
        self.worker: Optional[MissionPipelineWorker] = None

        self._init_ui()
        self._connect_signals()
        self._setup_shortcuts()

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
            ("EVIDENCE", 1),
            ("TIMELINE", 2),
            ("HEALTH", 3),
            ("SETTINGS", 4),
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
        self.stack.addWidget(self.console_view)  # 0

        self.evidence_view = EvidenceView(self)
        self.stack.addWidget(self.evidence_view)  # 1

        self.timeline_view = TimelineView(self)
        self.stack.addWidget(self.timeline_view)  # 2

        self.health_view = HealthView(self)
        self.stack.addWidget(self.health_view)  # 3

        self.settings_view = SettingsView(on_test_voice=self.test_voice_guidance, parent=self)
        self.stack.addWidget(self.settings_view)  # 4

        body_layout.addWidget(self.stack, stretch=1)
        root_layout.addLayout(body_layout, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.status_bar.setStyleSheet(f"background-color: {Colors.BG_PANEL}; color: {Colors.TEXT_MUTED}; font-size: 11px;")
        self.status_bar.showMessage("ASTRA-EA v0.1.0 (Phase 6 Mission Console) | Air-Gapped Local Operation | Optical Source Ready")
        self.setStatusBar(self.status_bar)

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

    def start_mission(self) -> None:
        """Launch the background pipeline worker."""
        if self.worker is not None and self.worker.isRunning():
            return

        self.worker = MissionPipelineWorker(
            bridge=self.bridge,
            procedure_path=self.procedure_path,
            camera_source=self.camera_source,
            camera_profile=self.camera_profile,
            session_id=self.session_id,
            voice_manager=self.voice_manager,
            parent=self,
        )
        self.worker.start()
        self.session_bar.set_session_state("RUNNING", self.session_id)

    def pause_mission(self) -> None:
        """Pause or resume the pipeline worker."""
        if self.worker:
            self.worker.pause()
            self.session_bar.set_session_state("PAUSED", self.session_id)

    def stop_mission(self) -> None:
        """Stop background execution."""
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.session_bar.set_session_state("READY", self.session_id)

    def test_voice_guidance(self) -> None:
        """Test audio guidance utterance."""
        self.voice_manager.speak("Testing ASTRA-EA audio guidance channel. Systems nominal.", priority=AudioPriority.INFO)

    # =========================================================================
    # Backend Bridge Event Handlers (Executed on Main Qt UI Thread)
    # =========================================================================

    def _on_frame_ready(self, frame_np, perception_state) -> None:
        self.console_view.video_panel.update_frame(frame_np, perception_state)

    def _on_step_progress(self, proc_state) -> None:
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
        if next_step:
            self.console_view.step_panel.update_next_action(f"Prepare for {next_step.replace('_', ' ').title()}")
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
                items.append(
                    EvidenceItemState(
                        evidence_type=factor,
                        score=item.score,
                        is_satisfied=item.is_satisfied,
                        details=item.details or "",
                        timestamp=time.time(),
                        source_frame=item.source_frame,
                    )
                )
        score = bundle.score if hasattr(bundle, "score") else 0.0
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

    def closeEvent(self, event) -> None:
        """Clean shutdown upon window close."""
        self.stop_mission()
        if self.voice_manager:
            self.voice_manager.shutdown()
        event.accept()

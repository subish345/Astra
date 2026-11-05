# ==============================================================================
# ORBITA Video Recordings & Archive View
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Full-screen interactive video recordings archive, player, and procedural replayer."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.common.config import get_project_root
from core.common.logging import get_logger
from core.mission.database import DatabaseManager
from core.ui.theme import Colors

logger = get_logger("recordings_view")


class RecordingsView(QWidget):
    """Archive browser and integrated player for video recordings and evidence clips."""

    def __init__(
        self,
        on_verify_video: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.on_verify_video = on_verify_video

        root = get_project_root()
        db_path = root / "storage" / "database" / "astra.db"
        if not db_path.exists():
            db_path = root / "storage" / "astra.db"
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        # Video Player State
        self.current_video_path: Optional[str] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_playing: bool = False
        self.total_frames: int = 0
        self.fps: float = 30.0
        self.playback_speed: float = 1.0
        self.current_frame_idx: int = 0

        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._on_play_tick)

        self._init_ui()
        self.refresh_recordings()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(10)

        # ---------------------------------------------------------------------
        # Top Header Bar
        # ---------------------------------------------------------------------
        hdr_frame = QFrame()
        hdr_frame.setObjectName("PanelFrame")
        hdr_layout = QHBoxLayout(hdr_frame)
        hdr_layout.setContentsMargins(12, 8, 12, 8)

        lbl_title = QLabel("EXPERIMENT VIDEO RECORDINGS ARCHIVE")
        lbl_title.setObjectName("HeaderTitle")
        hdr_layout.addWidget(lbl_title)

        self.lbl_count_badge = QLabel("0 SESSIONS")
        self.lbl_count_badge.setStyleSheet(
            f"font-size: 11px; font-weight: bold; color: {Colors.BLUE_BRIGHT}; "
            f"background-color: {Colors.BG_SURFACE}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-radius: 4px; padding: 3px 8px;"
        )
        hdr_layout.addWidget(self.lbl_count_badge)

        hdr_layout.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_recordings)
        hdr_layout.addWidget(self.btn_refresh)

        self.btn_delete = QPushButton("🗑 Delete")
        self.btn_delete.setStyleSheet(
            "background-color: #3f1212; color: #fca5a5; border: 1px solid #ef4444; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px; font-weight: bold;"
        )
        self.btn_delete.setToolTip("Remove selected recording from database archive")
        self.btn_delete.clicked.connect(self._delete_selected_recording)
        hdr_layout.addWidget(self.btn_delete)

        self.btn_clean = QPushButton("🧹 Clean Missing")
        self.btn_clean.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_SECONDARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )
        self.btn_clean.setToolTip("Purge database records where the video file no longer exists on disk")
        self.btn_clean.clicked.connect(self._clean_missing_recordings)
        hdr_layout.addWidget(self.btn_clean)

        self.btn_open_folder = QPushButton("📁 Open Folder")
        self.btn_open_folder.clicked.connect(self._open_recordings_folder)
        hdr_layout.addWidget(self.btn_open_folder)

        root_layout.addWidget(hdr_frame)

        # ---------------------------------------------------------------------
        # Main Splitter: Left Table + Right Player & Inspector
        # ---------------------------------------------------------------------
        splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Recordings Table
        left_frame = QFrame()
        left_frame.setObjectName("PanelFrame")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(8, 8, 8, 8)

        lbl_tbl_hdr = QLabel("RECORDED VIDEO SESSIONS (DATABASE AUDIT)")
        lbl_tbl_hdr.setObjectName("SectionTitle")
        left_layout.addWidget(lbl_tbl_hdr)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["RUN ID / SEGMENT", "DATE / TIME", "DURATION", "FRAMES", "STATUS"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.setStyleSheet(
            f"QTableWidget {{ background-color: {Colors.BG_DARKEST}; border: 1px solid {Colors.BORDER_DEFAULT}; }} "
            f"QTableWidget::item {{ padding: 6px; font-size: 11px; }} "
            f"QTableWidget::item:selected {{ background-color: #1e3a5f; color: #ffffff; }}"
        )
        left_layout.addWidget(self.table)
        splitter.addWidget(left_frame)

        # Right Panel: Player & Inspector
        right_frame = QFrame()
        right_frame.setObjectName("PanelFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(8)

        # Video Canvas
        self.video_canvas = QLabel("Select a video from the list to preview")
        self.video_canvas.setAlignment(Qt.AlignCenter)
        self.video_canvas.setMinimumSize(480, 270)
        self.video_canvas.setStyleSheet(
            f"background-color: #05070a; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-radius: 4px; color: {Colors.TEXT_MUTED}; font-size: 13px; font-weight: bold;"
        )
        right_layout.addWidget(self.video_canvas, stretch=3)

        # Video Scrubber Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        right_layout.addWidget(self.slider)

        # Playback Controls Bar
        ctrl_layout = QHBoxLayout()

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setObjectName("PrimaryButton")
        self.btn_play.clicked.connect(self.toggle_play)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_stop_video = QPushButton("⏹ Stop")
        self.btn_stop_video.clicked.connect(self.stop_playback)
        ctrl_layout.addWidget(self.btn_stop_video)

        lbl_speed = QLabel("Speed:")
        lbl_speed.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY}; margin-left: 6px;")
        ctrl_layout.addWidget(lbl_speed)

        self.cmb_speed = QComboBox()
        self.cmb_speed.addItems(["1.0x (Normal)", "0.5x (Slow)", "0.25x (Quarter)", "1.5x (Fast)", "2.0x (Double)"])
        self.cmb_speed.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; color: {Colors.TEXT_PRIMARY}; "
            f"border: 1px solid {Colors.BORDER_DEFAULT}; border-radius: 4px; padding: 2px 6px; font-size: 11px;"
        )
        self.cmb_speed.currentIndexChanged.connect(self._on_speed_changed)
        ctrl_layout.addWidget(self.cmb_speed)

        self.lbl_time = QLabel("00:00 / 00:00 | Frame: 0 / 0")
        self.lbl_time.setStyleSheet(f"font-size: 11px; font-family: monospace; color: {Colors.TEXT_SECONDARY}; margin-left: 6px;")
        ctrl_layout.addWidget(self.lbl_time)

        ctrl_layout.addStretch()

        self.btn_verify_this = QPushButton("🔍 Verify Movement Accuracy")
        self.btn_verify_this.setStyleSheet(
            "background-color: #1e3a5f; color: #93c5fd; border: 1px solid #3b82f6; "
            "border-radius: 4px; padding: 5px 12px; font-weight: bold;"
        )
        self.btn_verify_this.clicked.connect(self._on_verify_clicked)
        ctrl_layout.addWidget(self.btn_verify_this)

        right_layout.addLayout(ctrl_layout)

        # Info & Metadata Card
        self.meta_frame = QFrame()
        self.meta_frame.setStyleSheet(
            f"background-color: {Colors.BG_SURFACE}; border: 1px solid {Colors.BORDER_DEFAULT}; "
            f"border-radius: 4px; padding: 8px;"
        )
        meta_layout = QVBoxLayout(self.meta_frame)
        meta_layout.setContentsMargins(8, 6, 8, 6)

        self.lbl_meta_path = QLabel("Path: None")
        self.lbl_meta_path.setStyleSheet(f"font-size: 11px; font-family: monospace; color: {Colors.TEXT_PRIMARY};")
        self.lbl_meta_path.setWordWrap(True)
        meta_layout.addWidget(self.lbl_meta_path)

        self.lbl_meta_info = QLabel("Details: No video selected")
        self.lbl_meta_info.setStyleSheet(f"font-size: 11px; color: {Colors.TEXT_SECONDARY};")
        meta_layout.addWidget(self.lbl_meta_info)

        right_layout.addWidget(self.meta_frame, stretch=1)
        splitter.addWidget(right_frame)

        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        root_layout.addWidget(splitter, stretch=1)

    # -------------------------------------------------------------------------
    # Data Loading & List Operations
    # -------------------------------------------------------------------------

    def refresh_recordings(self) -> None:
        """Fetch real video recordings from SQLite database and data/recordings directory."""
        root = get_project_root()
        db_segments = self.db.get_video_segments(limit=200)

        entries: List[Dict[str, Any]] = []
        seen_paths = set()

        # 1. First add valid segments from database where file exists on disk
        for seg in db_segments:
            fpath_str = seg.get("file_path")
            if not fpath_str:
                continue
            vpath = Path(fpath_str).resolve()
            if not vpath.exists():
                continue
            resolved_str = str(vpath)
            if resolved_str not in seen_paths:
                seen_paths.add(resolved_str)
                entries.append(seg)

        # 2. Scan data/recordings directory for user recordings
        rec_dir = root / "data" / "recordings"
        if rec_dir.exists():
            for vf in sorted(rec_dir.glob("*.mp4")):
                v_res = str(vf.resolve())
                if v_res not in seen_paths:
                    seen_paths.add(v_res)
                    fc = 0
                    dur = 0.0
                    f_fps = 30.0
                    try:
                        c = cv2.VideoCapture(str(vf))
                        if c.isOpened():
                            fc = int(c.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
                            f_fps = float(c.get(cv2.CAP_PROP_FPS) or 30.0)
                            if fc > 0 and f_fps > 0:
                                dur = round(fc / f_fps, 2)
                            c.release()
                    except Exception:
                        pass

                    entries.append({
                        "segment_id": f"REC_{vf.stem}",
                        "run_id": vf.stem,
                        "start_time": datetime.fromtimestamp(vf.stat().st_mtime, timezone.utc).isoformat(),
                        "file_path": str(vf),
                        "frame_count": fc,
                        "fps": f_fps,
                        "duration_sec": dur,
                        "is_evidence_clip": 0,
                    })

        self.table.setRowCount(len(entries))
        self.lbl_count_badge.setText(f"{len(entries)} SESSIONS")

        for row, item in enumerate(entries):
            # Run ID item
            id_txt = item.get("run_id") or item.get("segment_id") or "UNKNOWN"
            it_id = QTableWidgetItem(id_txt)
            it_id.setForeground(Qt.white)
            it_id.setData(Qt.UserRole, item)
            self.table.setItem(row, 0, it_id)

            # Date / Time
            raw_time = item.get("start_time", "")
            time_txt = str(raw_time)[:19].replace("T", " ") if raw_time else "---"
            it_time = QTableWidgetItem(time_txt)
            it_time.setForeground(Qt.lightGray)
            self.table.setItem(row, 1, it_time)

            # Duration
            dur_val = item.get("duration_sec", 0.0) or 0.0
            dur_txt = f"{dur_val:.1f}s" if dur_val > 0 else "---"
            it_dur = QTableWidgetItem(dur_txt)
            it_dur.setForeground(Qt.yellow)
            self.table.setItem(row, 2, it_dur)

            # Frame count
            fc_val = item.get("frame_count", 0) or 0
            fc_txt = f"{fc_val} frames" if fc_val > 0 else "---"
            it_fc = QTableWidgetItem(fc_txt)
            it_fc.setForeground(Qt.cyan)
            self.table.setItem(row, 3, it_fc)

            # Status
            fpath = Path(item.get("file_path", ""))
            status_txt = "AVAILABLE" if fpath.exists() else "FILE_MISSING"
            it_st = QTableWidgetItem(status_txt)
            it_st.setForeground(Qt.green if fpath.exists() else Qt.red)
            self.table.setItem(row, 4, it_st)

        if len(entries) > 0:
            self.table.selectRow(0)
        else:
            self.video_canvas.clear()
            self.video_canvas.setText("No recorded video sessions.\nUse 🔴 REC or 📁 Upload Video to create recordings.")
            self.lbl_meta_path.setText("Path: None")
            self.lbl_meta_info.setText("Details: No recordings found")

    def _delete_selected_recording(self) -> None:
        """Delete currently selected video recording from database and disk."""
        row = self.table.currentRow()
        if row < 0:
            return

        it = self.table.item(row, 0)
        if not it:
            return
        item_data = it.data(Qt.UserRole) or {}
        seg_id = item_data.get("segment_id", "")
        run_id = item_data.get("run_id", seg_id)
        fpath_str = item_data.get("file_path", "")
        fpath = Path(fpath_str) if fpath_str else None

        if self.isVisible():
            confirm = QMessageBox.question(
                self,
                "Delete Recording",
                f"Are you sure you want to remove recording '{run_id}' from the database archive?\n\nFile: {fpath_str}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return

        # Stop playback if currently viewing this video
        if self.current_video_path and fpath and str(Path(self.current_video_path).resolve()) == str(fpath.resolve()):
            self.stop_playback()
            if self.cap:
                self.cap.release()
                self.cap = None
            self.current_video_path = None
            self.video_canvas.clear()
            self.video_canvas.setText("Select a video from the list to preview")
            self.lbl_meta_path.setText("Path: None")
            self.lbl_meta_info.setText("Details: No video selected")

        # Delete database entry
        if seg_id:
            self.db.delete_video_segment(seg_id)
        if fpath_str:
            self.db.delete_video_segments_by_path(fpath_str)

        # Delete file from disk if located in data/recordings directory
        root = get_project_root()
        rec_dir = root / "data" / "recordings"
        if fpath and fpath.exists():
            try:
                # Only delete if inside data/recordings to prevent deleting source demo assets
                if rec_dir.resolve() in fpath.resolve().parents:
                    fpath.unlink(missing_ok=True)
            except Exception as exc:
                logger.warning("Could not delete file %s: %s", fpath, exc)

        self.refresh_recordings()

    def _clean_missing_recordings(self) -> None:
        """Remove database segments referencing files that no longer exist."""
        removed = self.db.purge_missing_video_segments()
        self.refresh_recordings()
        if self.isVisible():
            QMessageBox.information(
                self,
                "Clean Missing Recordings",
                f"Cleaned {removed} missing or orphan video segment records from database.",
            )

    def _open_recordings_folder(self) -> None:
        """Open local recordings directory in system desktop file explorer."""
        root = get_project_root()
        rec_dir = root / "data" / "recordings"
        rec_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(rec_dir)])
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Video Playback Engine
    # -------------------------------------------------------------------------

    def _on_table_selection_changed(self) -> None:
        """User selected a row in the table: load video into player."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        item = self.table.item(row, 0)
        if not item:
            return
        data: Dict[str, Any] = item.data(Qt.UserRole)
        fpath_str = data.get("file_path")
        if not fpath_str:
            return

        self.load_video(fpath_str, data)

    def load_video(self, video_path: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Open video file and prepare player canvas."""
        self.stop_playback()

        vpath = Path(video_path).resolve()
        self.current_video_path = str(vpath)

        if not vpath.exists():
            self.video_canvas.setText(f"File missing on disk:\n{vpath}")
            self.lbl_meta_path.setText(f"Path: {vpath} (NOT FOUND)")
            return

        self.cap = cv2.VideoCapture(str(vpath))
        if not self.cap.isOpened():
            self.video_canvas.setText(f"Failed opening video format:\n{vpath.name}")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        fps_read = self.cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps_read if (fps_read and 1.0 <= fps_read <= 120.0) else 30.0
        self.current_frame_idx = 0

        self.slider.setRange(0, max(0, self.total_frames - 1))
        self.slider.setValue(0)

        # Update metadata display
        file_sz_mb = vpath.stat().st_size / (1024 * 1024)
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        dur_sec = self.total_frames / self.fps

        self.lbl_meta_path.setText(f"Path: {vpath}")
        self.lbl_meta_info.setText(
            f"Resolution: {w}x{h} | FPS: {self.fps:.1f} | Duration: {dur_sec:.1f}s | "
            f"Frames: {self.total_frames} | Size: {file_sz_mb:.2f} MB"
        )

        # Show first frame
        self._show_frame_at(0)

    def _show_frame_at(self, frame_idx: int) -> None:
        """Seek and render specific frame."""
        if not self.cap or not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.current_frame_idx = frame_idx
            self._render_pixmap(frame)
            self._update_time_label()

    def _render_pixmap(self, frame_bgr: np.ndarray) -> None:
        """Render OpenCV BGR frame onto the QLabel canvas."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qimg)

        target_size = self.video_canvas.size()
        scaled = pix.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_canvas.setPixmap(scaled)

    def _update_time_label(self) -> None:
        cur_sec = self.current_frame_idx / max(1.0, self.fps)
        tot_sec = self.total_frames / max(1.0, self.fps)
        cur_m, cur_s = divmod(int(cur_sec), 60)
        tot_m, tot_s = divmod(int(tot_sec), 60)
        self.lbl_time.setText(
            f"{cur_m:02d}:{cur_s:02d} / {tot_m:02d}:{tot_s:02d} | "
            f"Frame: {self.current_frame_idx}/{self.total_frames}"
        )

    def _on_speed_changed(self, idx: int) -> None:
        """Adjust playback speed multiplier."""
        speeds = [1.0, 0.5, 0.25, 1.5, 2.0]
        self.playback_speed = speeds[idx] if idx < len(speeds) else 1.0
        if self.is_playing:
            interval_ms = max(10, int((1000.0 / max(1.0, self.fps)) / self.playback_speed))
            self.play_timer.setInterval(interval_ms)

    def toggle_play(self) -> None:
        """Toggle video playback."""
        if not self.cap or not self.cap.isOpened():
            return

        if self.is_playing:
            self.is_playing = False
            self.play_timer.stop()
            self.btn_play.setText("▶ Play")
        else:
            if self.current_frame_idx >= self.total_frames - 1:
                self.current_frame_idx = 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.is_playing = True
            interval_ms = max(10, int((1000.0 / max(1.0, self.fps)) / self.playback_speed))
            self.play_timer.start(interval_ms)
            self.btn_play.setText("⏸ Pause")

    def stop_playback(self) -> None:
        """Stop playback and rewind to beginning."""
        self.is_playing = False
        self.play_timer.stop()
        self.btn_play.setText("▶ Play")
        if self.cap and self.cap.isOpened():
            self._show_frame_at(0)
            self.slider.setValue(0)

    def _on_play_tick(self) -> None:
        """Periodic timer event during playback."""
        if not self.cap or not self.cap.isOpened():
            self.stop_playback()
            return

        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.current_frame_idx += 1
            self._render_pixmap(frame)
            self.slider.blockSignals(True)
            self.slider.setValue(self.current_frame_idx)
            self.slider.blockSignals(False)
            self._update_time_label()

            if self.current_frame_idx >= self.total_frames - 1:
                self.stop_playback()
        else:
            self.stop_playback()

    def _on_slider_moved(self, value: int) -> None:
        """Operator scrubbed the timeline slider."""
        self._show_frame_at(value)

    def _on_verify_clicked(self) -> None:
        """Send currently loaded video to the Mission Console for procedure verification."""
        if not self.current_video_path:
            return
        self.stop_playback()
        if self.on_verify_video:
            self.on_verify_video(self.current_video_path)

    def hideEvent(self, event) -> None:
        """Pause playback whenever operator navigates away from recordings view."""
        self.stop_playback()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        """Ensure video capture and timers are released upon closing."""
        self.stop_playback()
        if self.cap:
            self.cap.release()
            self.cap = None
        super().closeEvent(event)


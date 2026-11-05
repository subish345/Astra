"""Unified Video Recording Service for Pramman.

Provides thread-safe, non-blocking asynchronous video session recording and clip extraction
used uniformly across Onboard Core, Mission Console, Ground Monitor, and Simulation.
"""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from core.common.logging import get_logger

logger = get_logger("RECORDING")


class UnifiedRecordingManager:
    """Thread-safe asynchronous video recorder for experiment sessions."""

    def __init__(self, base_dir: str = "data/recordings", max_queue_size: int = 120) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_queue_size = max_queue_size

        self._frame_queue: queue.Queue[Optional[Tuple[np.ndarray, int]]] = queue.Queue(maxsize=max_queue_size)
        self._worker_thread: Optional[threading.Thread] = None
        self._is_recording: bool = False
        self._stop_event = threading.Event()

        self._current_run_id: Optional[str] = None
        self._current_filepath: Optional[Path] = None
        self._start_time: Optional[float] = None
        self._start_mono: Optional[float] = None
        self._writer: Optional[cv2.VideoWriter] = None

        self._frames_written: int = 0
        self._frames_queued: int = 0
        self._dropped_frames: int = 0
        self._fps: int = 30
        self._resolution: Tuple[int, int] = (1280, 720)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def frames_written(self) -> int:
        return self._frames_written

    @property
    def current_file(self) -> Optional[Path]:
        return self._current_filepath

    def start_recording(
        self,
        run_id: str,
        fps: int = 30,
        resolution: Tuple[int, int] = (640, 480),
        codec: str = "mp4v",
    ) -> Path:
        """Commence recording for an active experiment run."""
        if self._is_recording:
            logger.warning("Recording already in progress for run: %s", self._current_run_id)
            return self._current_filepath or (self.base_dir / f"{run_id}.mp4")

        self._start_time = time.time()
        self._start_mono = time.monotonic()
        self._current_run_id = run_id
        self._fps = max(1, fps)
        self._resolution = resolution

        target_name = f"{run_id}.mp4"
        if (self.base_dir / target_name).exists():
            target_name = f"{run_id}_{int(self._start_time)}.mp4"
        self._current_filepath = self.base_dir / target_name

        # Drain any residual frames
        while not self._frame_queue.empty():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                break

        self._frames_written = 0
        self._frames_queued = 0
        self._dropped_frames = 0
        self._stop_event.clear()
        self._is_recording = True

        fourcc = cv2.VideoWriter_fourcc(*codec)
        self._writer = cv2.VideoWriter(
            str(self._current_filepath),
            fourcc,
            float(self._fps),
            self._resolution,
        )

        self._worker_thread = threading.Thread(target=self._writer_loop, daemon=True, name="VideoWriterWorker")
        self._worker_thread.start()

        logger.info("Started session recording: %s (%dx%d @ %d FPS)", self._current_filepath, resolution[0], resolution[1], fps)
        return self._current_filepath

    def record_frame(self, frame: np.ndarray, timestamp: Optional[float] = None) -> bool:
        """Push video frame into non-blocking writer queue with timestamp pacing to maintain real-time speed."""
        if not self._is_recording or frame is None:
            return False

        now = timestamp if timestamp is not None else time.monotonic()
        if self._start_mono is None or self._frames_queued == 0:
            self._start_mono = now
            self._start_time = time.time()

        # Maintain exact 1.0x real-time speed: compute expected frames up to this moment
        elapsed = max(0.0, now - self._start_mono)
        expected_total = max(1, int(round(elapsed * self._fps)) + 1)
        repeat_count = max(1, expected_total - self._frames_queued)
        # Cap repeat count to 3 seconds of frames max to prevent queue spikes
        repeat_count = min(repeat_count, int(self._fps * 3))

        try:
            self._frame_queue.put_nowait((frame.copy(), repeat_count))
            self._frames_queued += repeat_count
            return True
        except queue.Full:
            self._dropped_frames += 1
            return False

    def _writer_loop(self) -> None:
        """Background worker writing frames to disk."""
        while not self._stop_event.is_set() or not self._frame_queue.empty():
            try:
                item = self._frame_queue.get(timeout=0.1)
                if item is None:
                    break

                frame, count = item
                if self._writer is not None and self._writer.isOpened():
                    # Ensure matching resolution
                    if (frame.shape[1], frame.shape[0]) != self._resolution:
                        frame = cv2.resize(frame, self._resolution, interpolation=cv2.INTER_LINEAR)
                    for _ in range(count):
                        self._writer.write(frame)
                        self._frames_written += 1
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("Error writing video frame: %s", e)

        if self._writer is not None:
            self._writer.release()
            self._writer = None

    def stop_recording(self, db_manager: Optional[Any] = None) -> Optional[Path]:
        """Finalize and flush video file to disk, optionally persisting to database."""
        if not self._is_recording:
            return self._current_filepath

        self._stop_event.set()
        try:
            self._frame_queue.put_nowait(None)
        except Exception:
            pass
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)

        self._is_recording = False
        duration_sec = (self._frames_written / max(1.0, float(self._fps))) if self._frames_written > 0 else 0.0

        if db_manager and self._current_filepath and self._frames_written > 0:
            try:
                from datetime import datetime, timezone
                db_manager.record_video_segment(
                    segment_id=f"SEG_{self._current_run_id}_{int(time.time())}",
                    run_id=self._current_run_id,
                    start_time=datetime.fromtimestamp(self._start_time or time.time(), timezone.utc),
                    end_time=datetime.now(timezone.utc),
                    file_path=str(self._current_filepath),
                    frame_count=self._frames_written,
                    fps=float(self._fps),
                    duration_sec=round(duration_sec, 2),
                    is_evidence_clip=False,
                )
            except Exception as e:
                logger.error("Failed persisting video segment to database: %s", e)

        logger.info("Finalized video recording: %s (%d frames written, %d dropped)", self._current_filepath, self._frames_written, self._dropped_frames)
        return self._current_filepath

    def get_status(self) -> Dict[str, Any]:
        """Return operational telemetry."""
        return {
            "is_recording": self._is_recording,
            "run_id": self._current_run_id,
            "output_file": str(self._current_filepath) if self._current_filepath else None,
            "frames_written": self._frames_written,
            "dropped_frames": self._dropped_frames,
            "queue_depth": self._frame_queue.qsize(),
            "target_fps": self._fps,
        }

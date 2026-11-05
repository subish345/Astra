"""Real Data Collection Session Recorder.

Records video sessions from camera feeds along with synchronized metadata,
scenario flags, viewpoint profiles, and event logs.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from core.camera.webcam import WebcamSource
from core.camera.file_source import VideoFileSource
from core.dataset.schema import ScenarioType, SessionMetadata


class DatasetSessionRecorder:
    """Manages recording of a dataset collection session."""

    def __init__(
        self,
        base_dir: str = "datasets/raw/real",
        software_version: str = "0.1.0",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.software_version = software_version
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def record_session(
        self,
        source: str = "0",
        session_id: Optional[str] = None,
        experiment_id: str = "DEMO_EXP_001",
        camera_profile: str = "VIEW_LEFT",
        scenario: str = "CORRECT",
        operator_id: Optional[str] = None,
        notes: str = "",
        max_frames: Optional[int] = None,
        max_duration_sec: Optional[float] = None,
        interactive_display: bool = False,
    ) -> Dict[str, Any]:
        """Record video session and persist metadata and event stream."""
        if not session_id:
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            session_id = f"SESSION_{timestamp_str}"

        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        annotations_dir = session_dir / "annotations"
        annotations_dir.mkdir(parents=True, exist_ok=True)

        video_path = session_dir / "video.mp4"
        metadata_path = session_dir / "metadata.json"
        events_path = session_dir / "events.json"

        # Validate scenario enum
        try:
            scenario_type = ScenarioType(scenario.upper())
        except ValueError:
            scenario_type = ScenarioType.CORRECT

        # Initialize video capture source
        if source.isdigit():
            cam_src = WebcamSource(device_index=int(source), width=640, height=480, target_fps=30.0)
            src_type = "WEBCAM"
        else:
            cam_src = VideoFileSource(file_path=source)
            src_type = "VIDEO_FILE"

        success, msg = cam_src.open()
        if not success:
            raise RuntimeError(f"Failed to open video source '{source}': {msg}")

        writer: Optional[cv2.VideoWriter] = None
        events: List[Dict[str, Any]] = []
        frame_count = 0
        start_time = time.time()

        try:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")

            while True:
                # Check limits
                elapsed = time.time() - start_time
                if max_duration_sec and elapsed >= max_duration_sec:
                    break
                if max_frames and frame_count >= max_frames:
                    break

                ret, frame = cam_src.read_frame()
                if not ret or frame is None:
                    break

                h, w = frame.shape[:2]
                if writer is None:
                    writer = cv2.VideoWriter(str(video_path), fourcc, 30.0, (w, h))

                writer.write(frame)
                frame_count += 1

                # Record periodic frame event
                if frame_count % 30 == 0:
                    events.append({
                        "frame_index": frame_count,
                        "timestamp": round(elapsed, 3),
                        "status": "RECORDING",
                    })

                if interactive_display:
                    display_frame = frame.copy()
                    hud_text = f"REC | {session_id} | {scenario_type.value} | F:{frame_count} | {elapsed:.1f}s"
                    cv2.putText(
                        display_frame,
                        hud_text,
                        (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.65,
                        (0, 0, 255),
                        2,
                    )
                    cv2.imshow("ASTRA Dataset Recorder (Press 'q' to stop)", display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("q"):
                        break

        finally:
            cam_src.close()
            if writer is not None:
                writer.release()
            if interactive_display:
                cv2.destroyAllWindows()

        end_time = time.time()
        duration_sec = round(end_time - start_time, 2)

        # Build and save session metadata
        meta = SessionMetadata(
            session_id=session_id,
            experiment_id=experiment_id,
            procedure_version="1.0.0",
            camera_profile=camera_profile.upper(),
            source=src_type,
            scenario=scenario_type,
            operator_id=operator_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            software_version=self.software_version,
            notes=notes,
            frame_count=frame_count,
            duration_sec=duration_sec,
        )

        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        with open(events_path, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)

        return {
            "session_id": session_id,
            "session_dir": str(session_dir),
            "video_path": str(video_path),
            "metadata_path": str(metadata_path),
            "frame_count": frame_count,
            "duration_sec": duration_sec,
            "scenario": scenario_type.value,
        }

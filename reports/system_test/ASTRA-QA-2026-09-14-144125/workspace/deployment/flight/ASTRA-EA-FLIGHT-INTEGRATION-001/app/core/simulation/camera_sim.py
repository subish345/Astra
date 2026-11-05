"""Simulated Camera Source with Real-Time Fault Injection.

Implements CameraSource interface, feeding synthetic or recorded video frames
while applying dynamic, scheduled optical, environmental, and behavioral fault triggers.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

from core.camera.interface import CameraSource, FrameData
from core.dataset.generator import SyntheticDatasetGenerator
from core.simulation.faults import FaultInjectors
from core.simulation.scenario import FaultTrigger, FaultType, SimulationScenario


class SimulatedCameraSource(CameraSource):
    """Camera source supporting scripted fault injection and dynamic viewpoint switching."""

    def __init__(
        self,
        scenario: SimulationScenario,
        width: int = 640,
        height: int = 480,
        realtime_pacing: bool = False,
    ) -> None:
        self.scenario = scenario
        self.width = width
        self.height = height
        self.realtime_pacing = realtime_pacing

        self._active = False
        self._status = "CLOSED"
        self._frame_id = 0
        self._sim_time = 0.0
        self._dropped_frames = 0
        self._last_valid_frame: Optional[np.ndarray] = None
        self._active_camera_profile = scenario.camera_profile

        # Synthetic generator for real-time dynamic scene generation
        self._generator = SyntheticDatasetGenerator(
            output_dir="datasets/raw/synthetic/sim_temp",
            experiment_id="DEMO_EXP_001",
            width=width,
            height=height,
        )

        self._start_wall: Optional[datetime] = None
        self._start_mono: Optional[float] = None
        self._last_read_mono: Optional[float] = None

    def start(self) -> bool:
        """Initialize simulation stream."""
        self._active = True
        self._status = "OPEN"
        self._frame_id = 0
        self._sim_time = 0.0
        self._dropped_frames = 0
        self._active_camera_profile = self.scenario.camera_profile
        self._start_wall = datetime.now(timezone.utc)
        self._start_mono = time.monotonic()
        self._last_read_mono = self._start_mono
        return True

    def stop(self) -> None:
        """Terminate simulation stream."""
        self._active = False
        self._status = "CLOSED"

    def read(self) -> Optional[FrameData]:
        """Produce the next video frame with applied fault injections."""
        if not self._active:
            return None

        # Check total duration limit
        dt = 1.0 / max(1.0, self.scenario.target_fps)
        self._sim_time = self._frame_id * dt
        if self._sim_time >= self.scenario.duration_sec:
            self._status = "CLOSED"
            self._active = False
            return None

        now_mono = time.monotonic()
        now_wall = datetime.now(timezone.utc)

        # Realtime pacing sleep if requested
        if self.realtime_pacing and self._last_read_mono is not None:
            elapsed = now_mono - self._last_read_mono
            if elapsed < dt:
                time.sleep(dt - elapsed)
            now_mono = time.monotonic()
        self._last_read_mono = now_mono

        # 1. Identify active faults for the current simulation clock
        active_faults = [f for f in self.scenario.faults if f.is_active(self._sim_time)]

        # Check for Viewpoint Switch fault
        for f in active_faults:
            if f.fault_type == FaultType.VIEWPOINT_SWITCH:
                target_view = f.target or ("VIEW_RIGHT" if self._active_camera_profile == "VIEW_LEFT" else "VIEW_LEFT")
                self._active_camera_profile = target_view

        # Check for Frame Drop fault
        for f in active_faults:
            if f.fault_type == FaultType.FRAME_DROP:
                if np.random.rand() <= f.frequency:
                    self._dropped_frames += 1
                    self._frame_id += 1
                    # A dropped frame returns None in CameraSource interface
                    return None

        # Check for Frame Freeze fault
        for f in active_faults:
            if f.fault_type == FaultType.FRAME_FREEZE and self._last_valid_frame is not None:
                self._frame_id += 1
                return FrameData(
                    frame_id=self._frame_id,
                    image=self._last_valid_frame.copy(),
                    timestamp_mono=now_mono,
                    timestamp_wall=now_wall,
                    source_id=self.get_source_id(),
                )

        # Check for Black Frame fault
        for f in active_faults:
            if f.fault_type == FaultType.BLACK_FRAME:
                self._frame_id += 1
                black_img = FaultInjectors.apply_black_frame((self.height, self.width, 3))
                return FrameData(
                    frame_id=self._frame_id,
                    image=black_img,
                    timestamp_mono=now_mono,
                    timestamp_wall=now_wall,
                    source_id=self.get_source_id(),
                )

        # 2. Render base scene with procedural generator
        scene_seed = self.scenario.synthetic_seed + self._frame_id * 13
        scenario_mode = "CORRECT"

        # Check if behavioral wrong object fault is active
        for f in active_faults:
            if f.fault_type == FaultType.WRONG_OBJECT:
                scenario_mode = "WRONG_OBJECT"
            elif f.fault_type == FaultType.SKIPPED_STEP:
                scenario_mode = "SKIPPED"
            elif f.fault_type == FaultType.INCOMPLETE_ACTION:
                scenario_mode = "INCOMPLETE"

        img, _ = self._generator._render_scene(
            sample_id=f"SIM_{self._frame_id:06d}",
            session_id=self.scenario.scenario_id,
            camera_profile=self._active_camera_profile,
            scenario=scenario_mode,
            scene_seed=scene_seed,
            frame_seq=self._frame_id,
        )

        # 3. Apply active optical and degradation filters
        for f in active_faults:
            if f.fault_type == FaultType.LOW_LIGHT:
                img = FaultInjectors.apply_low_light(img, f.intensity)
            elif f.fault_type == FaultType.GLARE:
                img = FaultInjectors.apply_glare(img, f.intensity)
            elif f.fault_type == FaultType.OCCLUSION:
                img = FaultInjectors.apply_occlusion(img, f.intensity)
            elif f.fault_type == FaultType.LENS_SMUDGE:
                img = FaultInjectors.apply_lens_smudge(img, f.intensity)
            elif f.fault_type == FaultType.NOISE_CORRUPTION:
                img = FaultInjectors.apply_noise(img, f.intensity)
            elif f.fault_type == FaultType.MOTION_BLUR:
                img = FaultInjectors.apply_motion_blur(img, f.intensity)
            elif f.fault_type == FaultType.WRONG_OBJECT:
                img = FaultInjectors.apply_wrong_object_swap(img, f.intensity)
            elif f.fault_type == FaultType.LATENCY_SPIKE:
                FaultInjectors.apply_latency_spike(f.intensity)

        self._frame_id += 1
        self._last_valid_frame = img.copy()

        return FrameData(
            frame_id=self._frame_id,
            image=img,
            timestamp_mono=now_mono,
            timestamp_wall=now_wall,
            source_id=self.get_source_id(),
        )

    def get_status(self) -> str:
        return self._status

    def get_fps(self) -> float:
        return self.scenario.target_fps

    def get_resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)

    def get_source_id(self) -> str:
        return f"SIM_{self.scenario.scenario_id}_{self._active_camera_profile}"

    def get_dropped_frames(self) -> int:
        return self._dropped_frames

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def current_camera_profile(self) -> str:
        return self._active_camera_profile

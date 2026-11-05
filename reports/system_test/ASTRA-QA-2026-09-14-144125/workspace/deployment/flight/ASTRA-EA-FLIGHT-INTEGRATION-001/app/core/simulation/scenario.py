"""Simulation Scenario and Fault Trigger Schema Definitions.

Defines typed configurations for mission simulations, injected fault profiles,
and validation expectations.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class FaultType(str, Enum):
    """Categorized fault types injected during simulation."""
    # Optical / Sensor Faults
    FRAME_DROP = "FRAME_DROP"
    FRAME_FREEZE = "FRAME_FREEZE"
    BLACK_FRAME = "BLACK_FRAME"
    NOISE_CORRUPTION = "NOISE_CORRUPTION"
    LOW_LIGHT = "LOW_LIGHT"
    GLARE = "GLARE"
    OCCLUSION = "OCCLUSION"
    LENS_SMUDGE = "LENS_SMUDGE"
    MOTION_BLUR = "MOTION_BLUR"

    # Behavioral / Operator Faults
    WRONG_OBJECT = "WRONG_OBJECT"
    WRONG_ORDER = "WRONG_ORDER"
    SKIPPED_STEP = "SKIPPED_STEP"
    INCOMPLETE_ACTION = "INCOMPLETE_ACTION"

    # Perception & Latency Faults
    LATENCY_SPIKE = "LATENCY_SPIKE"
    BBOX_JITTER = "BBOX_JITTER"
    DETECTOR_DROPOUT = "DETECTOR_DROPOUT"

    # System & Viewpoint Faults
    VIEWPOINT_SWITCH = "VIEWPOINT_SWITCH"
    STORAGE_FAILURE = "STORAGE_FAILURE"


class FaultTrigger(BaseModel):
    """Configuration for an individual timed fault injection."""
    fault_type: FaultType
    start_time: float = Field(default=0.0, description="Start time in seconds from simulation start")
    duration_sec: float = Field(default=2.0, description="Duration in seconds for which fault persists")
    intensity: float = Field(default=0.75, ge=0.0, le=1.0, description="Intensity of fault effect (0.0 to 1.0)")
    frequency: float = Field(default=1.0, ge=0.0, le=1.0, description="Trigger probability per eligible frame")
    target: Optional[str] = Field(default=None, description="Specific target object or perspective")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional fault-specific parameters")

    def is_active(self, current_time: float) -> bool:
        """Check if fault should be active at the given simulation time."""
        return self.start_time <= current_time < (self.start_time + self.duration_sec)


class SimulationScenario(BaseModel):
    """Specification for a simulated mission test scenario."""
    scenario_id: str = "SIM_NOMINAL_001"
    name: str = "Nominal Mission Run"
    description: str = "Nominal procedural execution without intentional errors"
    procedure_path: str = "configs/experiments/demo.yaml"
    camera_profile: str = "VIEW_LEFT"
    duration_sec: float = 12.0
    target_fps: float = 30.0
    synthetic_seed: int = 12345
    video_source_path: Optional[str] = None
    faults: List[FaultTrigger] = Field(default_factory=list)
    expected_final_status: str = "VERIFIED"  # VERIFIED, DEVIATION, UNCERTAIN
    expected_deviations: List[str] = Field(default_factory=list)

    @classmethod
    def load_yaml(cls, path: str | Path) -> SimulationScenario:
        """Load scenario from YAML configuration file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Scenario configuration file not found: '{file_path}'")
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def save_yaml(self, path: str | Path) -> None:
        """Save scenario to YAML configuration file."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, sort_keys=False)

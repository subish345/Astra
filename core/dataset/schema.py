"""Dataset Schema Definitions for ASTRA-EA.

Defines typed schemas for object detection, activity, procedure annotations,
session metadata, and dataset manifests.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnnotationSource(str, Enum):
    """Source of truth for annotations."""
    HUMAN = "HUMAN"
    SYNTHETIC = "SYNTHETIC"
    AI_ASSISTED = "AI_ASSISTED"
    IMPORTED = "IMPORTED"


class ScenarioType(str, Enum):
    """Experiment scenario types."""
    CORRECT = "CORRECT"
    WRONG_OBJECT = "WRONG_OBJECT"
    WRONG_ORDER = "WRONG_ORDER"
    SKIPPED = "SKIPPED"
    INCOMPLETE = "INCOMPLETE"
    UNCERTAIN = "UNCERTAIN"
    RECOVERY = "RECOVERY"


class BoundingBox(BaseModel):
    """Bounding box in pixel coordinates [x1, y1, x2, y2]."""
    x1: float
    y1: float
    x2: float
    y2: float

    def to_list(self) -> List[float]:
        return [self.x1, self.y1, self.x2, self.y2]

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height


class DetectedObjectAnnotation(BaseModel):
    """Individual object annotation within an image frame."""
    class_name: str
    bbox: List[float] = Field(..., description="[x1, y1, x2, y2]")
    track_id: Optional[int] = None
    confidence: float = 1.0
    attributes: Dict[str, Any] = Field(default_factory=dict)


class FrameDetectionAnnotation(BaseModel):
    """Object detection ground truth for a single image."""
    sample_id: str
    image_path: str
    session_id: str
    camera_profile: str = "VIEW_LEFT"
    scenario: ScenarioType = ScenarioType.CORRECT
    source: AnnotationSource = AnnotationSource.SYNTHETIC
    width: int = 640
    height: int = 480
    timestamp: float = 0.0
    objects: List[DetectedObjectAnnotation] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActivityAnnotation(BaseModel):
    """Temporal activity annotation for a video sequence."""
    video: str
    activity: str = Field(..., description="APPROACH, TOUCH, GRASP, LIFT, HOLD, MOVE, PLACE, RELEASE")
    object: str
    actor: str = "ASTRONAUT"
    start_frame: int
    end_frame: int
    start_time: float = 0.0
    end_time: float = 0.0
    source: AnnotationSource = AnnotationSource.HUMAN


class ProcedureAnnotation(BaseModel):
    """Procedure execution ground truth."""
    experiment: str = "DEMO_EXP_001"
    step: str
    status: str = "VERIFIED"
    start_time: float
    end_time: float
    source: AnnotationSource = AnnotationSource.HUMAN


class SessionMetadata(BaseModel):
    """Metadata recorded for a real or synthetic experiment session."""
    session_id: str
    experiment_id: str = "DEMO_EXP_001"
    procedure_version: str = "1.0.0"
    camera_profile: str = "VIEW_LEFT"
    source: str = "WEBCAM"
    scenario: ScenarioType = ScenarioType.CORRECT
    operator_id: Optional[str] = None
    timestamp: str = ""
    software_version: str = "0.1.0"
    notes: str = ""
    frame_count: int = 0
    duration_sec: float = 0.0


class DatasetSplit(BaseModel):
    """Session-level split mapping."""
    train: List[str] = Field(default_factory=list, description="List of sample IDs or session IDs")
    validation: List[str] = Field(default_factory=list)
    test: List[str] = Field(default_factory=list)


class DatasetManifest(BaseModel):
    """Comprehensive dataset manifest (dataset_manifest.json)."""
    dataset_id: str
    version: str
    created_at: str
    source: str = "HYBRID"  # REAL, SYNTHETIC, HYBRID
    experiment: str = "DEMO_EXP_001"
    classes: List[str] = Field(default_factory=lambda: ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"])
    sample_count: int = 0
    session_count: int = 0
    camera_profiles: List[str] = Field(default_factory=list)
    scenarios: List[str] = Field(default_factory=list)
    annotation_schema: str = "ASTRA_DETECTION_v1"
    generator_version: Optional[str] = None
    splits: DatasetSplit = Field(default_factory=DatasetSplit)
    provenance: Dict[str, Any] = Field(default_factory=dict)

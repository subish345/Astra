"""Activity annotation schema and serialization for future Dataset Studio ingestion.

Formats recognized activity episodes into standardized machine-readable labels.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from core.activity.types import ActivityObservation


class ActivityAnnotation(BaseModel):
    """Standardized activity annotation format for training datasets and ground truth validation."""
    video_id: str
    activity: str
    actor: str
    object: str
    start_frame: int = Field(default=0, ge=0)
    end_frame: int = Field(default=0, ge=0)
    start_time: float = Field(default=0.0, ge=0.0)
    end_time: float = Field(default=0.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    annotation_source: str = Field(default="auto_pipeline")  # "human", "auto_pipeline", "synthetic"
    primitives: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_observation(
        cls,
        obs: ActivityObservation,
        video_id: str = "SESSION_LIVE",
        start_frame: int = 0,
        end_frame: int = 0,
        annotation_source: str = "auto_pipeline",
    ) -> ActivityAnnotation:
        """Construct an annotation record from an ActivityObservation."""
        return cls(
            video_id=video_id,
            activity=obs.activity_name,
            actor=obs.actor,
            object=obs.target_object_id,
            start_frame=start_frame,
            end_frame=end_frame,
            start_time=round(obs.start_time, 3),
            end_time=round(obs.end_time, 3),
            confidence=round(obs.confidence, 3),
            annotation_source=annotation_source,
            primitives=list(obs.primitives),
            metadata=obs.evidence_refs,
        )


def export_annotations_json(annotations: List[ActivityAnnotation], output_path: str | Path) -> None:
    """Export a list of ActivityAnnotations to a formatted JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [ann.model_dump() for ann in annotations]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_annotations_jsonl(annotations: List[ActivityAnnotation], output_path: str | Path) -> None:
    """Export a list of ActivityAnnotations to JSON-Lines format."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ann in annotations:
            f.write(ann.model_dump_json() + "\n")

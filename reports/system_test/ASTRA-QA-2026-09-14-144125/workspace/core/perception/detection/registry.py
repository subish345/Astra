"""Model and dataset registry for ASTRA-EA.

Tracks model metadata, versions, target tasks, input resolutions, and verifies
checkpoint artifacts for mission reproducibility and auditability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from core.common.config import get_project_root
from core.common.logging import get_logger

logger = get_logger("PERCEPTION")


@dataclass
class ModelMetadata:
    """Metadata specification for a registered deep-learning model."""
    id: str
    name: str
    version: str
    task: str  # "object_detection", "pose_estimation", "hand_detection", "tracking"
    framework: str  # "onnx", "pytorch", "opencv"
    classes: List[str] = field(default_factory=list)
    input_resolution: Optional[List[int]] = None
    weights_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetMetadata:
    """Metadata specification for training and benchmark datasets."""
    id: str
    name: str
    version: str
    split: str  # "train", "val", "test"
    sample_count: int = 0
    classes: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelRegistry:
    """Registry maintaining traceable models and dataset versions."""

    def __init__(self, config_dir: Optional[Path] = None):
        root = get_project_root()
        self.config_dir = config_dir or (root / "models/configs")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, ModelMetadata] = {}

    def register(self, metadata: ModelMetadata) -> None:
        """Register model metadata."""
        self._models[f"{metadata.id}:{metadata.version}"] = metadata
        logger.info("Model registered: %s v%s (%s)", metadata.name, metadata.version, metadata.task)

    def get_model(self, model_id: str, version: Optional[str] = None) -> Optional[ModelMetadata]:
        """Lookup model by ID and optional version."""
        if version:
            return self._models.get(f"{model_id}:{version}")
        # Return latest matching
        matching = [m for k, m in self._models.items() if m.id == model_id]
        return matching[-1] if matching else None

    def verify_weights(self, metadata: ModelMetadata) -> bool:
        """Verify existence and accessibility of model checkpoint file."""
        if not metadata.weights_path:
            return False
        root = get_project_root()
        path = Path(metadata.weights_path)
        if not path.is_absolute():
            path = root / path
        return path.exists() and path.is_file()

    def list_models(self) -> List[ModelMetadata]:
        """Return all registered models."""
        return list(self._models.values())

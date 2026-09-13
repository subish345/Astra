"""Model Registry and Lifecycle Management for ASTRA-EA.

Maintains model provenance, versioning, performance metrics, and lifecycle states:
TRAINING -> CANDIDATE -> VALIDATED -> DEPLOYMENT_CANDIDATE -> RETIRED.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelStatus(str, Enum):
    TRAINING = "TRAINING"
    CANDIDATE = "CANDIDATE"
    VALIDATED = "VALIDATED"
    DEPLOYMENT_CANDIDATE = "DEPLOYMENT_CANDIDATE"
    RETIRED = "RETIRED"


class ModelRecord(BaseModel):
    """Registered model artifact record."""
    model_id: str
    version: str
    type: str = "OBJECT_DETECTION"  # OBJECT_DETECTION, ACTIVITY_RECOGNITION
    dataset_version: str
    training_run: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    input_size: List[int] = Field(default_factory=lambda: [640, 480])
    latency_ms: float = 0.0
    fps: float = 0.0
    memory_mb: float = 0.0
    status: ModelStatus = ModelStatus.CANDIDATE
    classes: List[str] = Field(default_factory=lambda: ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"])
    checkpoint_path: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: str = ""


class ModelRegistry:
    """Persistent registry for versioned AI models."""

    def __init__(self, registry_dir: str = "models/registry") -> None:
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.registry_dir / "models.json"

    def _load_db(self) -> Dict[str, Dict[str, Any]]:
        if not self.registry_file.exists():
            return {}
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_db(self, db: Dict[str, Dict[str, Any]]) -> None:
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)

    def register_model(self, record: ModelRecord) -> ModelRecord:
        """Register or update a model record."""
        db = self._load_db()
        record.updated_at = datetime.now(timezone.utc).isoformat()
        db[record.model_id] = record.model_dump()
        self._save_db(db)
        return record

    def get_model(self, model_id: str) -> Optional[ModelRecord]:
        """Fetch model by model_id."""
        db = self._load_db()
        if model_id in db:
            return ModelRecord.model_validate(db[model_id])
        return None

    def list_models(self, status: Optional[ModelStatus] = None) -> List[ModelRecord]:
        """List all models, optionally filtered by lifecycle status."""
        db = self._load_db()
        records = [ModelRecord.model_validate(v) for v in db.values()]
        if status:
            records = [r for r in records if r.status == status]
        return sorted(records, key=lambda x: x.created_at, reverse=True)

    def update_status(self, model_id: str, new_status: ModelStatus) -> ModelRecord:
        """Transition model lifecycle status with validation gating."""
        record = self.get_model(model_id)
        if not record:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        # Enforcement Rule: Only models with validated test metrics can become VALIDATED or DEPLOYMENT_CANDIDATE
        if new_status in {ModelStatus.VALIDATED, ModelStatus.DEPLOYMENT_CANDIDATE}:
            if not record.metrics:
                raise ValueError(
                    f"Cannot promote model '{model_id}' to {new_status.value}: no evaluation metrics recorded."
                )
            if not record.dataset_version or not record.training_run:
                raise ValueError(
                    f"Cannot promote model '{model_id}' to {new_status.value}: missing provenance metadata."
                )

        record.status = new_status
        return self.register_model(record)

    def set_deployment_candidate(self, model_id: str) -> ModelRecord:
        """Mark model as the active DEPLOYMENT_CANDIDATE, demoting previous one."""
        current_candidates = self.list_models(status=ModelStatus.DEPLOYMENT_CANDIDATE)
        for cand in current_candidates:
            if cand.model_id != model_id:
                cand.status = ModelStatus.VALIDATED
                self.register_model(cand)

        return self.update_status(model_id, ModelStatus.DEPLOYMENT_CANDIDATE)

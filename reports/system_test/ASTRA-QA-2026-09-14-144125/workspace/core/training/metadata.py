"""Training Reproducibility and Run Metadata.

Records immutable provenance for training runs: hyperparameters, dataset version,
hardware devices, framework versions, duration, and metrics.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def get_git_commit_hash() -> Optional[str]:
    """Retrieve active git commit hash if within a git repo."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        return out if out else None
    except Exception:
        return None


class EpochMetrics(BaseModel):
    """Metrics recorded for a single epoch."""
    epoch: int
    train_loss: float
    val_loss: float
    val_precision: float
    val_recall: float
    val_mAP50: float
    per_class_mAP: Dict[str, float] = Field(default_factory=dict)
    epoch_duration_sec: float = 0.0


class TrainingRunMetadata(BaseModel):
    """Provenance and execution records for a training run."""
    run_id: str
    dataset_version: str
    model_name: str
    model_architecture: str
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    random_seed: int = 42
    python_version: str = Field(default_factory=lambda: f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    pytorch_version: Optional[str] = None
    cuda_version: Optional[str] = None
    device_used: str = "CPU"
    gpu_name: Optional[str] = None
    vram_mb: Optional[int] = None
    git_commit: Optional[str] = Field(default_factory=get_git_commit_hash)
    start_time: str = ""
    end_time: str = ""
    training_duration_sec: float = 0.0
    epochs_completed: int = 0
    best_epoch: int = 0
    best_metric_value: float = 0.0
    primary_metric: str = "val_mAP50"
    epoch_history: List[EpochMetrics] = Field(default_factory=list)
    saved_checkpoints: List[str] = Field(default_factory=list)
    status: str = "COMPLETED"  # RUNNING, COMPLETED, FAILED

    def save(self, run_dir: Path) -> Path:
        """Save metadata to run_dir/training_run.json."""
        run_dir.mkdir(parents=True, exist_ok=True)
        file_path = run_dir / "training_run.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
        return file_path

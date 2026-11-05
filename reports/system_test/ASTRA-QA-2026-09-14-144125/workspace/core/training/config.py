"""Training Configuration Schema.

Defines typed configuration options for training object detection and activity models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """Configuration for a model training execution run."""
    model_name: str = "ASTRA_OBJECT_DETECTOR"
    architecture: str = "ASTRA_DETECTION_NET"
    dataset_version: str = "ASTRA-DATASET-v0.1"
    classes: List[str] = Field(
        default_factory=lambda: ["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"]
    )
    epochs: int = 10
    batch_size: Union[int, str] = 8
    image_size: int = 640
    learning_rate: float = 0.001
    weight_decay: float = 1e-4
    device: str = "auto"  # "auto", "cuda", "cpu"
    seed: int = 42
    primary_metric: str = "val_mAP50"
    early_stopping_patience: int = 5
    checkpoint_interval: int = 1
    description: str = "ASTRA-EA focused experiment object detector training"
    extra_params: Dict[str, Any] = Field(default_factory=dict)

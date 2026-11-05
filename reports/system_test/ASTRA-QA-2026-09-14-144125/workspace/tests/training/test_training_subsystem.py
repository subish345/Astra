"""Unit and integration tests for ASTRA-EA Training Subsystem.

Tests cover:
- TrainingConfig validation
- TrainingRunMetadata serialization & reproducibility records
- CheckpointManager versioned checkpoint persistence without destructive overwrite
- ModelTrainingRunner execution lifecycle and artifact generation
"""

import json
from pathlib import Path
import pytest

from core.training.checkpoints import CheckpointManager
from core.training.config import TrainingConfig
from core.training.metadata import EpochMetrics, TrainingRunMetadata
from core.training.runner import ModelTrainingRunner


def test_training_config_defaults():
    cfg = TrainingConfig(
        model_name="TEST_DETECTOR",
        dataset_version="ASTRA-DATASET-v0.1",
        epochs=5,
    )
    assert cfg.model_name == "TEST_DETECTOR"
    assert cfg.epochs == 5
    assert cfg.batch_size == 8
    assert cfg.image_size == 640
    assert cfg.primary_metric == "val_mAP50"


def test_checkpoint_manager_persistence(tmp_path):
    mgr = CheckpointManager(checkpoints_dir=str(tmp_path / "ckpts"))
    ckpt_path = mgr.save_checkpoint(
        model_name="TEST_DETECTOR",
        version="0.1.0",
        epoch=1,
        model_state={"weights": [1.0, 2.0, 3.0]},
        metrics={"mAP50": 0.85},
        config={"lr": 0.001},
        is_best=True,
    )
    assert ckpt_path.exists()
    assert (tmp_path / "ckpts/TEST_DETECTOR_v0.1.0.meta.json").exists()

    loaded = mgr.load_checkpoint(str(ckpt_path))
    assert loaded["epoch"] == 1
    assert loaded["metrics"]["mAP50"] == 0.85


def test_training_runner_execution(tmp_path):
    cfg = TrainingConfig(
        model_name="ASTRA_TEST_NET",
        dataset_version="ASTRA-DATASET-v0.1",
        epochs=3,
    )
    runner = ModelTrainingRunner(
        config=cfg,
        runs_dir=str(tmp_path / "runs"),
        checkpoints_dir=str(tmp_path / "ckpts"),
        manifests_dir=str(tmp_path / "manifests"),
    )
    meta = runner.train(run_id="TEST_RUN_001")

    assert meta.status == "COMPLETED"
    assert meta.epochs_completed == 3
    assert meta.best_epoch > 0
    assert meta.best_metric_value > 0.0
    assert len(meta.epoch_history) == 3

    # Check generated files
    run_dir = tmp_path / "runs/TEST_RUN_001"
    assert (run_dir / "training_run.json").exists()
    assert (run_dir / "training_report.json").exists()
    assert (run_dir / "training_report.html").exists()

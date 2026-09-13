"""Configuration management system for ASTRA-EA.

Loads and validates YAML configuration files using Pydantic, supporting environment
variable overrides and ensuring zero magic numbers in application source code.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class SystemSettings(BaseModel):
    environment: str = Field(default="development")
    offline_mode: bool = Field(default=True)
    device_name: str = Field(default="ASTRA-EA Ground Demonstrator")
    log_level: str = Field(default="INFO")
    log_to_file: bool = Field(default=True)
    log_file_path: str = Field(default="storage/reports/astra.log")


class DatabaseSettings(BaseModel):
    path: str = Field(default="storage/database/astra.db")
    timeout_seconds: float = Field(default=10.0, ge=1.0)
    enable_wal_mode: bool = Field(default=True)


class CameraSettings(BaseModel):
    config_path: str = Field(default="configs/cameras/default.yaml")


class CameraDeviceSettings(BaseModel):
    source_type: str = Field(default="webcam")  # "webcam" or "file"
    device_id: int = Field(default=0, ge=0)
    file_path: Optional[str] = Field(default=None)
    fps: int = Field(default=30, gt=0)
    width: int = Field(default=1280, gt=0)
    height: int = Field(default=720, gt=0)
    auto_reconnect: bool = Field(default=True)
    reconnect_delay_seconds: float = Field(default=2.0, ge=0.5)
    max_reconnect_attempts: int = Field(default=5, ge=1)
    buffer_size: int = Field(default=150, gt=10)


class StorageSettings(BaseModel):
    base_dir: str = Field(default="storage")
    video_dir: str = Field(default="storage/video")
    evidence_dir: str = Field(default="storage/evidence")
    reports_dir: str = Field(default="storage/reports")
    max_storage_gb: float = Field(default=50.0, gt=1.0)


class ThresholdSettings(BaseModel):
    min_detection_confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    min_pose_confidence: float = Field(default=0.60, ge=0.0, le=1.0)
    min_hand_confidence: float = Field(default=0.60, ge=0.0, le=1.0)
    min_evidence_score: float = Field(default=0.75, ge=0.0, le=1.0)
    temporal_window_seconds: float = Field(default=10.0, gt=1.0)
    uncertainty_timeout_seconds: float = Field(default=15.0, gt=1.0)


class VoiceSettings(BaseModel):
    enabled: bool = Field(default=True)
    engine: str = Field(default="pyttsx3")
    rate: int = Field(default=165, gt=50, lt=400)
    volume: float = Field(default=0.9, ge=0.0, le=1.0)
    cooldown_seconds: float = Field(default=3.5, ge=0.5)


class StreamingSettings(BaseModel):
    enabled: bool = Field(default=False)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8554, gt=1024, lt=65535)
    protocol: str = Field(default="rtsp")


class ActiveExperimentSettings(BaseModel):
    path: str = Field(default="configs/experiments/demo.yaml")


class AppConfig(BaseModel):
    """Root configuration model encapsulating all subsystem settings."""
    system: SystemSettings = Field(default_factory=SystemSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    camera: CameraSettings = Field(default_factory=CameraSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    thresholds: ThresholdSettings = Field(default_factory=ThresholdSettings)
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    streaming: StreamingSettings = Field(default_factory=StreamingSettings)
    active_experiment: ActiveExperimentSettings = Field(default_factory=ActiveExperimentSettings)

    @classmethod
    def load_from_yaml(cls, yaml_path: str | Path, project_root: Optional[Path] = None) -> AppConfig:
        """Load configuration from a YAML file, applying environment variable overrides."""
        path = Path(yaml_path)
        if not path.is_absolute() and project_root:
            path = project_root / path

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f) or {}

        # Apply environment variable overrides
        if "ASTRA_ENV" in os.environ:
            raw_data.setdefault("system", {})["environment"] = os.environ["ASTRA_ENV"]
        if "ASTRA_DB_PATH" in os.environ:
            raw_data.setdefault("database", {})["path"] = os.environ["ASTRA_DB_PATH"]
        if "ASTRA_LOG_LEVEL" in os.environ:
            raw_data.setdefault("system", {})["log_level"] = os.environ["ASTRA_LOG_LEVEL"]
        if "ASTRA_OFFLINE_MODE" in os.environ:
            raw_data.setdefault("system", {})["offline_mode"] = os.environ["ASTRA_OFFLINE_MODE"].lower() in ("true", "1")

        return cls(**raw_data)


def get_project_root() -> Path:
    """Return the absolute path of the repository root."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(config_path: Optional[str | Path] = None) -> AppConfig:
    """Convenience helper to load the active application configuration."""
    root = get_project_root()
    env_path = os.environ.get("ASTRA_CONFIG_PATH")
    target_path = Path(config_path or env_path or "configs/system.yaml")
    return AppConfig.load_from_yaml(target_path, project_root=root)


def load_camera_config(camera_config_path: Optional[str | Path] = None) -> CameraDeviceSettings:
    """Load camera device configuration file."""
    root = get_project_root()
    target_path = Path(camera_config_path or "configs/cameras/default.yaml")
    if not target_path.is_absolute():
        target_path = root / target_path

    if not target_path.exists():
        raise FileNotFoundError(f"Camera configuration file not found: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f) or {}

    cam_data = raw_data.get("camera", raw_data)
    return CameraDeviceSettings(**cam_data)

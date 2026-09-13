"""Unit tests for ASTRA-EA configuration subsystem."""

import os
from pathlib import Path
import pytest
from pydantic import ValidationError

from core.common.config import AppConfig, load_camera_config, load_config


def test_load_default_config(tmp_path):
    """Verify loading the real system configuration."""
    cfg = load_config()
    assert cfg.system.environment in ("development", "production", "testing")
    assert cfg.system.offline_mode is True
    assert cfg.thresholds.min_detection_confidence > 0.0
    assert cfg.database.path == "storage/database/astra.db"


def test_config_env_overrides(monkeypatch):
    """Verify environment variables take precedence over YAML defaults."""
    monkeypatch.setenv("ASTRA_ENV", "ci_testing")
    monkeypatch.setenv("ASTRA_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("ASTRA_DB_PATH", "storage/test.db")

    cfg = load_config()
    assert cfg.system.environment == "ci_testing"
    assert cfg.system.log_level == "DEBUG"
    assert cfg.database.path == "storage/test.db"


def test_missing_config_file():
    """Verify FileNotFoundError is raised for non-existent configs."""
    with pytest.raises(FileNotFoundError):
        AppConfig.load_from_yaml("non_existent_path.yaml")


def test_invalid_yaml_types(tmp_path):
    """Verify validation errors are raised when YAML contains invalid types."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("thresholds:\n  min_detection_confidence: 'not_a_float'\n")

    with pytest.raises(ValidationError):
        AppConfig.load_from_yaml(bad_yaml)


def test_load_camera_config():
    """Verify default camera device configuration loading."""
    cam_cfg = load_camera_config()
    assert cam_cfg.fps > 0
    assert cam_cfg.width > 0
    assert cam_cfg.height > 0
    assert cam_cfg.source_type in ("webcam", "file")

"""Unit tests for storage manager and safe filesystem layout."""

from pathlib import Path
import pytest

from storage.storage_manager import StorageManager


def test_storage_manager_initialization(tmp_path):
    """Verify directories are created properly within the designated root."""
    storage = StorageManager(base_dir="storage", project_root=tmp_path)
    assert storage.video_dir.exists()
    assert storage.evidence_dir.exists()
    assert storage.reports_dir.exists()
    assert storage.database_dir.exists()


def test_path_traversal_prevention(tmp_path):
    """Verify that path traversal attempts are detected and rejected."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        StorageManager(base_dir="../../outside_dir", project_root=tmp_path)


def test_evidence_clip_dir_sanitization(tmp_path):
    """Verify event ID sanitization when creating evidence directories."""
    storage = StorageManager(base_dir="storage", project_root=tmp_path)
    safe_dir = storage.get_evidence_clip_dir("EVT_001/../MALICIOUS")
    assert ".." not in safe_dir.name
    assert safe_dir.exists()


def test_storage_metrics_calculation(tmp_path):
    """Verify storage metrics calculation."""
    storage = StorageManager(base_dir="storage", max_storage_gb=25.0, project_root=tmp_path)
    metrics = storage.get_storage_metrics()
    assert "storage_used_gb" in metrics
    assert "disk_free_gb" in metrics
    assert metrics["storage_limit_gb"] == 25.0

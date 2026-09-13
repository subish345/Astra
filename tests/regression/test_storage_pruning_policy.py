"""Regression Test for FINDING-003 / CAPA-003: Storage pruning and evidence preservation."""

from pathlib import Path
import pytest

from core.platform.storage import StorageManager


def test_storage_pruning_protects_critical_evidence(tmp_path: Path) -> None:
    """Verify that pruning discards transient diagnostic logs while protecting verified evidence."""
    sm = StorageManager(base_dir=tmp_path / "flight_data")

    # Create diagnostic log file
    diag_file = sm.diagnostics_dir / "preview_trace_01.log"
    diag_file.write_text("DEBUG_FRAME_PREVIEW" * 500, encoding="utf-8")

    # Create critical evidence file
    ev_file = sm.evidence_dir / "STEP_01_VERIFICATION.jpg"
    ev_file.write_text("CRITICAL_STEP_EVIDENCE_PAYLOAD", encoding="utf-8")

    assert diag_file.is_file()
    assert ev_file.is_file()

    # Trigger priority pruning
    pruned = sm.prune_lowest_priority(target_free_mb=10.0)

    assert str(diag_file) in pruned
    assert not diag_file.exists()

    # CRITICAL INVARIANT: Evidence file must NOT be deleted
    assert ev_file.exists()
    assert ev_file.read_text(encoding="utf-8") == "CRITICAL_STEP_EVIDENCE_PAYLOAD"

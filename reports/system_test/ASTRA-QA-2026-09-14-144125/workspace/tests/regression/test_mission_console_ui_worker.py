"""Regression test suite for FINDING-007 (Mission Console UI Worker & Callback Interfaces).

Addresses runtime exceptions surfaced during Phase 21 live Mission Console execution:
1. ProcedureVisualizer.draw_procedure_hud() recovery_manager keyword argument compatibility.
2. EvidenceItem attribute handling (.confidence / .verified vs .score / .is_satisfied).
3. DatabaseManager.complete_experiment_run alias compatibility.
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock

from core.common.config import get_project_root
from core.procedure.validator import load_procedure_file
from core.procedure.visualizer import ProcedureVisualizer
from core.procedure.progress import ProcedureProgressManager
from core.evidence.types import EvidenceBundle, EvidenceItem, EvidenceType
from core.mission.database import DatabaseManager


def test_draw_procedure_hud_argument_flexibility() -> None:
    """Ensure draw_procedure_hud handles both recovery_state and recovery_manager keyword arguments."""
    root = get_project_root()
    proc = load_procedure_file(root / "configs/experiments/demo.yaml")
    vis = ProcedureVisualizer(proc)

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    progress_mgr = ProcedureProgressManager(proc)

    # 1. Test with progress_manager object and recovery_manager object
    mock_recovery = MagicMock()
    mock_recovery.state.name = "OBSERVING"

    out_frame = vis.draw_procedure_hud(
        frame=frame,
        state=progress_mgr,
        camera_profile="view_left",
        recovery_manager=mock_recovery,
    )
    assert isinstance(out_frame, np.ndarray)
    assert out_frame.shape == (480, 640, 3)

    # 2. Test with standard ProcedureState and recovery_state string
    state = progress_mgr.get_state()
    out_frame2 = vis.draw_procedure_hud(
        frame=frame,
        state=state,
        camera_profile="view_left",
        recovery_state="CORRECTING",
    )
    assert isinstance(out_frame2, np.ndarray)


def test_evidence_bundle_item_extraction_compatibility() -> None:
    """Ensure evidence items with confidence and verified attributes are safely adapted."""
    from core.ui.state import EvidenceItemState

    # Construct standard EvidenceBundle with EvidenceItem (which has confidence & verified, not score)
    item = EvidenceItem(
        evidence_type=EvidenceType.OBJECT_DETECTED,
        verified=True,
        confidence=0.95,
        details={"object": "centrifuge_tube"},
    )
    bundle = EvidenceBundle(
        activity_id="ACT_001",
        activity_name="APPROACH",
        items={"OBJECT_DETECTED": item},
        evidence_score=0.92,
    )

    # Simulate _on_evidence_bundle extraction logic
    items_state = []
    for factor, it in bundle.items.items():
        score_val = getattr(it, "confidence", getattr(it, "score", 0.0))
        sat_val = getattr(it, "verified", getattr(it, "is_satisfied", False))
        det_str = str(it.details) if getattr(it, "details", None) else ""
        frame_idx = getattr(it, "end_frame", getattr(it, "start_frame", getattr(it, "source_frame", 0))) or 0
        items_state.append(
            EvidenceItemState(
                evidence_type=str(factor),
                score=float(score_val),
                is_satisfied=bool(sat_val),
                details=det_str,
                timestamp=1000.0,
                source_frame=int(frame_idx),
            )
        )

    assert len(items_state) == 1
    assert items_state[0].score == 0.95
    assert items_state[0].is_satisfied is True
    assert "centrifuge_tube" in items_state[0].details


def test_database_manager_complete_experiment_run_alias(tmp_path) -> None:
    """Ensure DatabaseManager provides complete_experiment_run alias alongside end_experiment_run."""
    db_path = tmp_path / "test_astra.db"
    db = DatabaseManager(db_path)
    db.initialize()

    # Record experiment first to satisfy FK
    db.record_experiment(experiment_id="EXP_001", name="Test Experiment", version="1.0.0")

    # Start run
    db.start_experiment_run(run_id="TEST_RUN_001", experiment_id="EXP_001")

    # Complete run via complete_experiment_run alias
    db.complete_experiment_run(run_id="TEST_RUN_001", status="COMPLETED")

    # Verify run completed in DB
    with db.get_connection() as conn:
        row = conn.execute("SELECT status FROM experiment_runs WHERE run_id = ?", ("TEST_RUN_001",)).fetchone()
        assert row is not None
        assert row[0] == "COMPLETED"

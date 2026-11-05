"""Integration test for ASTRA-EA Phase 0/1 engineering foundation.

Verifies end-to-end orchestration:
Configuration -> Database -> Procedure Validation -> Event Contracts -> Health Telemetry -> Storage
"""

import os
from pathlib import Path
import pytest

from core.common.config import load_config
from core.health.manager import HealthManager
from core.health.types import HealthComponent, HealthState
from core.mission.database import DatabaseManager
from core.mission.events import (
    ActivityEvent,
    AlertEvent,
    AssistantPriority,
    DecisionType,
    EvidenceEvent,
    HealthEvent,
    ProcedureDecision,
)
from core.procedure.validator import load_procedure_file
from storage.storage_manager import StorageManager


def test_full_foundation_integration(tmp_path):
    """End-to-end validation of all Phase 0 and Phase 1 subsystems working in concert."""
    # 1. Load active system configuration
    cfg = load_config()
    assert cfg.system.offline_mode is True

    # 2. Initialize test database
    db_file = tmp_path / "integration_astra.db"
    db = DatabaseManager(db_file)
    db.initialize()

    # 3. Load and validate experiment procedure
    exp_def = load_procedure_file("configs/experiments/demo.yaml")
    assert exp_def.experiment.id == "DEMO_EXP_001"
    assert len(exp_def.steps) == 4

    # 4. Register experiment in database and start a run
    db.record_experiment(
        experiment_id=exp_def.experiment.id,
        name=exp_def.experiment.name,
        version=exp_def.experiment.version,
        description=exp_def.experiment.description,
    )
    session_id = "SESSION_TEST_001"
    db.start_experiment_run(session_id, exp_def.experiment.id, total_steps=len(exp_def.steps))

    # 5. Initialize Storage Manager
    storage = StorageManager(base_dir=tmp_path / "storage", project_root=tmp_path)
    storage.initialize_directories()

    # 6. Initialize Health Manager and verify normal state
    health_mgr = HealthManager()
    assert health_mgr.get_overall_health() == HealthState.NORMAL

    # 7. Simulate step 1 execution contracts
    step_01 = exp_def.steps[0]

    # Activity recognized
    act = ActivityEvent(
        run_id=session_id,
        activity_name=step_01.expected_actions[0],
        actor="ASTRONAUT",
        object_id=step_01.expected_objects[0],
        confidence=0.85,
        duration_seconds=3.2,
    )
    db.record_activity(act)

    # Evidence corroborated
    evd = EvidenceEvent(
        activity_ref=act.event_id,
        evidence_score=0.88,
        items={"astronaut_visible": True, "object_visible": True},
        is_conclusive=True,
    )
    db.record_evidence(evd)

    # Assurance decision formulated
    decision = ProcedureDecision(
        run_id=session_id,
        experiment_id=exp_def.experiment.id,
        step_id=step_01.id,
        sequence=step_01.sequence,
        decision=DecisionType.VERIFIED,
        confidence=0.88,
        reason="Approach to main workstation confirmed with high evidence",
        evidence_id=evd.event_id,
    )
    db.record_decision(decision)

    # Alert / Voice guidance dispatched
    alert = AlertEvent(
        run_id=session_id,
        priority=AssistantPriority.INFO,
        message=f"Step 1 verified: Proceed to Step 2 ({exp_def.steps[1].name})",
        spoken=True,
    )
    db.record_alert(alert)

    # Heartbeat logged
    hb = health_mgr.heartbeat(
        HealthComponent.ASSURANCE,
        state=HealthState.NORMAL,
        metrics={"eval_latency_ms": 1.2},
    )
    db.record_health(hb)

    # 8. Complete session run
    db.finish_experiment_run(session_id, status="COMPLETED", completed_steps=1, deviations=0)

    # 9. Verify database integrity
    recent_events = db.get_recent_events(run_id=session_id)
    assert len(recent_events) == 1
    assert recent_events[0]["decision"] == "VERIFIED"
    assert recent_events[0]["step_id"] == "STEP_01"

    with db.get_connection() as conn:
        run_row = conn.execute("SELECT * FROM experiment_runs WHERE run_id = ?", (session_id,)).fetchone()
        assert run_row["status"] == "COMPLETED"
        assert run_row["completed_steps"] == 1
        assert run_row["deviations_count"] == 0

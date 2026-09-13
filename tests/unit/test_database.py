"""Unit tests for SQLite database manager and audit schema."""

import sqlite3
import pytest

from core.mission.database import DatabaseManager
from core.mission.events import (
    ActivityEvent,
    AlertEvent,
    AssistantPriority,
    DecisionType,
    EvidenceEvent,
    HealthEvent,
    HealthState,
    ProcedureDecision,
)


@pytest.fixture
def test_db(tmp_path):
    """Fixture providing an initialized temporary database."""
    db_file = tmp_path / "test_astra.db"
    db = DatabaseManager(db_file)
    db.initialize()
    return db


def test_database_initialization(test_db):
    """Verify table creation upon initialization."""
    with test_db.get_connection() as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cursor.fetchall()}

    expected = {
        "schema_migrations",
        "experiments",
        "experiment_runs",
        "procedure_steps",
        "events",
        "activities",
        "evidence",
        "alerts",
        "system_health",
        "video_segments",
        "models",
        "datasets",
    }
    assert expected.issubset(tables)


def test_foreign_key_enforcement(test_db):
    """Verify that foreign key constraints are strictly enforced."""
    with pytest.raises(sqlite3.IntegrityError):
        # Attempt to insert an experiment_run for a non-existent experiment
        test_db.start_experiment_run("RUN_001", "NON_EXISTENT_EXP")


def test_record_experiment_and_run(test_db):
    """Verify registering an experiment and recording an active execution run."""
    test_db.record_experiment("EXP_TEST", "Test Exp", "1.0.0", "Test Description")
    test_db.start_experiment_run("RUN_001", "EXP_TEST", total_steps=3)

    with test_db.get_connection() as conn:
        row = conn.execute("SELECT * FROM experiment_runs WHERE run_id = 'RUN_001'").fetchone()
        assert row["experiment_id"] == "EXP_TEST"
        assert row["status"] == "IN_PROGRESS"
        assert row["total_steps"] == 3

    test_db.finish_experiment_run("RUN_001", status="COMPLETED", completed_steps=3, deviations=0)

    with test_db.get_connection() as conn:
        row = conn.execute("SELECT * FROM experiment_runs WHERE run_id = 'RUN_001'").fetchone()
        assert row["status"] == "COMPLETED"
        assert row["completed_steps"] == 3
        assert row["end_time"] is not None


def test_record_assurance_decision_and_query(test_db):
    """Verify recording and querying procedure assurance decisions."""
    test_db.record_experiment("EXP_TEST", "Test Exp", "1.0.0")
    test_db.start_experiment_run("RUN_001", "EXP_TEST")

    decision = ProcedureDecision(
        run_id="RUN_001",
        experiment_id="EXP_TEST",
        step_id="STEP_01",
        sequence=1,
        decision=DecisionType.VERIFIED,
        confidence=0.92,
        reason="Object and hand contact confirmed",
    )
    test_db.record_decision(decision)

    events = test_db.get_recent_events(run_id="RUN_001")
    assert len(events) == 1
    assert events[0]["event_id"] == decision.event_id
    assert events[0]["decision"] == "VERIFIED"
    assert events[0]["confidence"] == pytest.approx(0.92)


def test_record_multimodal_artifacts(test_db):
    """Verify recording activity, evidence, alert, and health records."""
    test_db.record_experiment("EXP_TEST", "Test Exp", "1.0.0")
    test_db.start_experiment_run("RUN_001", "EXP_TEST")

    # 1. Activity
    act = ActivityEvent(
        run_id="RUN_001",
        activity_name="GRASP",
        actor="ASTRONAUT",
        object_id="RED_BOX",
        confidence=0.88,
        duration_seconds=2.4,
    )
    test_db.record_activity(act)

    # 2. Evidence
    evd = EvidenceEvent(
        activity_ref=act.event_id,
        evidence_score=0.85,
        items={"object_detected": True, "contact_detected": True},
        is_conclusive=True,
    )
    test_db.record_evidence(evd)

    # 3. Alert
    alert = AlertEvent(
        run_id="RUN_001",
        priority=AssistantPriority.WARNING,
        message="Please select the Red Box",
        spoken=True,
    )
    test_db.record_alert(alert)

    # 4. Health
    health = HealthEvent(
        component="CAMERA",
        state=HealthState.NORMAL,
        metrics={"fps": 29.8, "latency_ms": 14.2},
    )
    test_db.record_health(health)

    # Verify counts in DB
    with test_db.get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM system_health").fetchone()[0] == 1

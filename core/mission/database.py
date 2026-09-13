"""SQLite audit database engine for ASTRA-EA.

Manages relational persistence of experiment definitions, session runs, steps,
decision events, evidence bundles, alerts, and system health heartbeats.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from core.common.logging import get_logger
from core.mission.events import (
    ActivityEvent,
    AlertEvent,
    EvidenceEvent,
    HealthEvent,
    MissionEvent,
    ProcedureDecision,
)

logger = get_logger("STORAGE")

SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS experiment_runs (
    run_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status TEXT NOT NULL, -- 'IN_PROGRESS', 'COMPLETED', 'ABORTED'
    total_steps INTEGER DEFAULT 0,
    completed_steps INTEGER DEFAULT 0,
    deviations_count INTEGER DEFAULT 0,
    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS procedure_steps (
    step_id TEXT NOT NULL,
    experiment_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    PRIMARY KEY (step_id, experiment_id),
    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT NOT NULL,
    step_id TEXT,
    decision TEXT,
    confidence REAL,
    payload TEXT,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    activity_id TEXT PRIMARY KEY,
    run_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    activity_name TEXT NOT NULL,
    actor TEXT NOT NULL,
    object_id TEXT,
    confidence REAL NOT NULL,
    duration_seconds REAL DEFAULT 0.0,
    evidence_ref TEXT,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    activity_ref TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    evidence_score REAL NOT NULL,
    items_json TEXT NOT NULL,
    is_conclusive INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    run_id TEXT,
    timestamp TIMESTAMP NOT NULL,
    priority TEXT NOT NULL,
    message TEXT NOT NULL,
    spoken INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS system_health (
    health_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    component TEXT NOT NULL,
    state TEXT NOT NULL,
    metrics_json TEXT
);

CREATE TABLE IF NOT EXISTS video_segments (
    segment_id TEXT PRIMARY KEY,
    run_id TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    file_path TEXT NOT NULL,
    is_evidence_clip INTEGER DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS models (
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    task TEXT NOT NULL,
    metrics_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_name, version)
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_name TEXT NOT NULL,
    version TEXT NOT NULL,
    split TEXT NOT NULL,
    sample_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (dataset_name, version, split)
);

-- Optimization indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS idx_activities_run_id ON activities (run_id);
CREATE INDEX IF NOT EXISTS idx_alerts_run_id ON alerts (run_id);
CREATE INDEX IF NOT EXISTS idx_health_component ON system_health (component, timestamp);
"""


class DatabaseManager:
    """Encapsulates SQLite connection lifecycle, migrations, and transactional inserts."""

    def __init__(self, db_path: str | Path, timeout: float = 10.0, enable_wal: bool = True):
        self.db_path = Path(db_path)
        self.timeout = timeout
        self.enable_wal = enable_wal
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for SQLite connections with foreign key enforcement and timeout."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=self.timeout,
        )
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON;")
            if self.enable_wal:
                conn.execute("PRAGMA journal_mode = WAL;")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        """Create database tables and apply initial migrations if not present."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            # Check migration
            cursor = conn.execute("SELECT version FROM schema_migrations WHERE version = ?", (SCHEMA_VERSION,))
            if not cursor.fetchone():
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (SCHEMA_VERSION,))
        logger.info("Database initialized successfully at %s (Schema v%d)", self.db_path, SCHEMA_VERSION)

    def record_experiment(self, experiment_id: str, name: str, version: str, description: Optional[str] = None) -> None:
        """Register an experiment definition in the database."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO experiments (experiment_id, name, version, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(experiment_id) DO UPDATE SET
                    name = excluded.name,
                    version = excluded.version,
                    description = excluded.description
                """,
                (experiment_id, name, version, description),
            )

    def start_experiment_run(self, run_id: str, experiment_id: str, total_steps: int = 0) -> None:
        """Record the initiation of an experiment execution session."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO experiment_runs (run_id, experiment_id, start_time, status, total_steps)
                VALUES (?, ?, ?, 'IN_PROGRESS', ?)
                """,
                (run_id, experiment_id, now, total_steps),
            )

    def finish_experiment_run(self, run_id: str, status: str = "COMPLETED", completed_steps: int = 0, deviations: int = 0) -> None:
        """Record the completion or abort of an experiment execution session."""
        now = datetime.now(timezone.utc).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE experiment_runs
                SET end_time = ?, status = ?, completed_steps = ?, deviations_count = ?
                WHERE run_id = ?
                """,
                (now, status, completed_steps, deviations, run_id),
            )

    def record_decision(self, decision: ProcedureDecision) -> None:
        """Persist a procedure assurance decision event."""
        payload = json.dumps({
            "sequence": decision.sequence,
            "deviation_reason": decision.deviation_reason.value if decision.deviation_reason else None,
            "reason": decision.reason,
            "evidence_id": decision.evidence_id,
        })
        ts = decision.timestamp.isoformat() if isinstance(decision.timestamp, datetime) else str(decision.timestamp)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO events (event_id, run_id, timestamp, event_type, step_id, decision, confidence, payload)
                VALUES (?, ?, ?, 'ASSURANCE_DECISION', ?, ?, ?, ?)
                """,
                (
                    decision.event_id,
                    decision.run_id,
                    ts,
                    decision.step_id,
                    decision.decision.value,
                    decision.confidence,
                    payload,
                ),
            )

    def record_activity(self, activity: ActivityEvent) -> None:
        """Persist a recognized physical activity event."""
        ts = activity.timestamp.isoformat() if isinstance(activity.timestamp, datetime) else str(activity.timestamp)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activities (activity_id, run_id, timestamp, activity_name, actor, object_id, confidence, duration_seconds, evidence_ref)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity.event_id,
                    activity.run_id,
                    ts,
                    activity.activity_name,
                    activity.actor,
                    activity.object_id,
                    activity.confidence,
                    activity.duration_seconds,
                    activity.evidence_ref,
                ),
            )

    def record_evidence(self, evidence: EvidenceEvent) -> None:
        """Persist an evidence bundle."""
        items_json = json.dumps(evidence.items)
        ts = evidence.timestamp.isoformat() if isinstance(evidence.timestamp, datetime) else str(evidence.timestamp)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence (evidence_id, activity_ref, timestamp, evidence_score, items_json, is_conclusive)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.event_id,
                    evidence.activity_ref,
                    ts,
                    evidence.evidence_score,
                    items_json,
                    1 if evidence.is_conclusive else 0,
                ),
            )

    def record_alert(self, alert: AlertEvent) -> None:
        """Persist an assistant alert notification."""
        ts = alert.timestamp.isoformat() if isinstance(alert.timestamp, datetime) else str(alert.timestamp)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO alerts (alert_id, run_id, timestamp, priority, message, spoken)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.event_id,
                    alert.run_id,
                    ts,
                    alert.priority.value,
                    alert.message,
                    1 if alert.spoken else 0,
                ),
            )

    def record_health(self, health: HealthEvent) -> None:
        """Persist a subsystem health heartbeat record."""
        metrics_json = json.dumps(health.metrics)
        ts = health.timestamp.isoformat() if isinstance(health.timestamp, datetime) else str(health.timestamp)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO system_health (timestamp, component, state, metrics_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    ts,
                    health.component,
                    health.state.value,
                    metrics_json,
                ),
            )

    def get_recent_events(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Query chronological events for the Mission Timeline and Ground Monitor."""
        with self.get_connection() as conn:
            if run_id:
                cursor = conn.execute(
                    "SELECT * FROM events WHERE run_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (run_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
            return [dict(row) for row in cursor.fetchall()]

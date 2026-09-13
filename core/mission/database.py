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

CREATE TABLE IF NOT EXISTS step_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL,
    confidence REAL NOT NULL,
    evidence_bundle_id TEXT,
    timestamp_start REAL,
    timestamp_end REAL,
    reasons_json TEXT,
    procedure_version TEXT,
    model_version TEXT,
    software_version TEXT,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evidence_bundles (
    bundle_id TEXT PRIMARY KEY,
    activity_id TEXT,
    step_id TEXT,
    activity_name TEXT,
    target_object_id TEXT,
    timestamp REAL,
    evidence_score REAL,
    confidence REAL,
    required_satisfied INTEGER,
    optional_satisfied INTEGER,
    missing_required_json TEXT,
    items_json TEXT,
    source_frames_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS procedure_progress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    timestamp REAL,
    current_step TEXT,
    previous_step TEXT,
    completed_steps_json TEXT,
    candidate_step TEXT,
    uncertain_step TEXT,
    next_expected_step TEXT,
    procedure_status TEXT NOT NULL,
    active_bundle_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES experiment_runs (run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS assurance_decisions (
    decision_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    camera_profile TEXT NOT NULL,
    step_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL NOT NULL,
    deviation_reason TEXT,
    reason TEXT,
    reasons_json TEXT,
    evidence_summary_json TEXT,
    recommended_recovery TEXT,
    severity TEXT,
    procedure_version TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recovery_events (
    context_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    deviation_reason TEXT NOT NULL,
    state TEXT NOT NULL,
    explanation TEXT,
    recommendation TEXT,
    target_step_id TEXT,
    detected_at REAL NOT NULL,
    resolved_at REAL,
    attempts INTEGER DEFAULT 1,
    verified_corrective_action INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ui_audit_events (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,
    details_json TEXT
);

-- Optimization indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events (run_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events (timestamp);
CREATE INDEX IF NOT EXISTS idx_activities_run_id ON activities (run_id);
CREATE INDEX IF NOT EXISTS idx_alerts_run_id ON alerts (run_id);
CREATE INDEX IF NOT EXISTS idx_health_component ON system_health (component, timestamp);
CREATE INDEX IF NOT EXISTS idx_evaluations_run_id ON step_evaluations (run_id);
CREATE INDEX IF NOT EXISTS idx_progress_run_id ON procedure_progress (run_id);
CREATE INDEX IF NOT EXISTS idx_assurance_session ON assurance_decisions (session_id);
CREATE INDEX IF NOT EXISTS idx_assurance_viewpoint ON assurance_decisions (camera_profile);
CREATE INDEX IF NOT EXISTS idx_recovery_session ON recovery_events (session_id);
CREATE INDEX IF NOT EXISTS idx_ui_audit_run ON ui_audit_events (run_id);
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

    def is_healthy(self) -> bool:
        """Check whether SQLite database is accessible and responsive."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1;")
                return cursor.fetchone() is not None
        except Exception:
            return False

    def close(self) -> None:
        """Close/checkpoint database connections."""
        pass

    def initialize(self) -> None:
        """Create database tables and apply initial migrations if not present."""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            # Check migration
            cursor = conn.execute("SELECT version FROM schema_migrations WHERE version = ?", (SCHEMA_VERSION,))
            if not cursor.fetchone():
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (SCHEMA_VERSION,))
        logger.info("Database initialized successfully at %s (Schema v%d)", self.db_path, SCHEMA_VERSION)

    def end_experiment_run(self, run_id: str, status: str = "COMPLETED", completed_steps: int = 0, deviations: int = 0) -> None:
        """Alias for finish_experiment_run for orchestrator compatibility."""
        self.finish_experiment_run(run_id, status=status, completed_steps=completed_steps, deviations=deviations)

    def complete_experiment_run(self, run_id: str, status: str = "COMPLETED", completed_steps: int = 0, deviations: int = 0) -> None:
        """Alias for finish_experiment_run for UI worker compatibility."""
        self.finish_experiment_run(run_id, status=status, completed_steps=completed_steps, deviations=deviations)


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
                ON CONFLICT(run_id) DO UPDATE SET
                    start_time = excluded.start_time,
                    status = excluded.status,
                    total_steps = excluded.total_steps
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

    def record_step_evaluation(self, evaluation: Any) -> None:
        """Persist a procedural step verification decision."""
        eval_dict = evaluation.to_dict() if hasattr(evaluation, "to_dict") else dict(evaluation)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO step_evaluations (
                    evaluation_id, experiment_id, run_id, step_id, status,
                    confidence, evidence_bundle_id, timestamp_start, timestamp_end,
                    reasons_json, procedure_version, model_version, software_version, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(evaluation_id) DO UPDATE SET
                    status = excluded.status,
                    confidence = excluded.confidence,
                    reasons_json = excluded.reasons_json
                """,
                (
                    eval_dict.get("evaluation_id"),
                    eval_dict.get("experiment_id"),
                    eval_dict.get("run_id"),
                    eval_dict.get("step_id"),
                    eval_dict.get("status"),
                    eval_dict.get("confidence", 0.0),
                    eval_dict.get("evidence_bundle_id"),
                    eval_dict.get("timestamp_start", 0.0),
                    eval_dict.get("timestamp_end", 0.0),
                    json.dumps(eval_dict.get("reasons", [])),
                    eval_dict.get("procedure_version", "1.0.0"),
                    eval_dict.get("model_version", "yolov8n-custom-0.1"),
                    eval_dict.get("software_version", "0.4.0"),
                    json.dumps(eval_dict.get("metadata", {})),
                ),
            )

    def record_evidence_bundle(self, bundle: Any) -> None:
        """Persist a multimodal evidence bundle."""
        b_dict = bundle.to_dict() if hasattr(bundle, "to_dict") else dict(bundle)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence_bundles (
                    bundle_id, activity_id, step_id, activity_name, target_object_id,
                    timestamp, evidence_score, confidence, required_satisfied,
                    optional_satisfied, missing_required_json, items_json, source_frames_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bundle_id) DO UPDATE SET
                    evidence_score = excluded.evidence_score,
                    confidence = excluded.confidence,
                    required_satisfied = excluded.required_satisfied,
                    items_json = excluded.items_json
                """,
                (
                    b_dict.get("bundle_id"),
                    b_dict.get("activity_id"),
                    b_dict.get("step_id"),
                    b_dict.get("activity_name"),
                    b_dict.get("target_object_id"),
                    b_dict.get("timestamp", 0.0),
                    b_dict.get("evidence_score", 0.0),
                    b_dict.get("confidence", 0.0),
                    1 if b_dict.get("required_satisfied") else 0,
                    1 if b_dict.get("optional_satisfied") else 0,
                    json.dumps(b_dict.get("missing_required", [])),
                    json.dumps(b_dict.get("items", {})),
                    json.dumps(b_dict.get("source_frames", [])),
                ),
            )

    def record_procedure_progress(self, state: Any) -> None:
        """Persist a procedure progress state transition snapshot."""
        s_dict = state.to_dict() if hasattr(state, "to_dict") else dict(state)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO procedure_progress (
                    experiment_id, run_id, timestamp, current_step, previous_step,
                    completed_steps_json, candidate_step, uncertain_step,
                    next_expected_step, procedure_status, active_bundle_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s_dict.get("experiment_id"),
                    s_dict.get("run_id"),
                    s_dict.get("timestamp", 0.0),
                    s_dict.get("current_step"),
                    s_dict.get("previous_step"),
                    json.dumps(s_dict.get("completed_steps", [])),
                    s_dict.get("candidate_step"),
                    s_dict.get("uncertain_step"),
                    s_dict.get("next_expected_step"),
                    s_dict.get("procedure_status", "READY"),
                    s_dict.get("active_bundle_id"),
                ),
            )

    def get_step_evaluations(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Query recent step evaluation decisions."""
        with self.get_connection() as conn:
            if run_id:
                cursor = conn.execute(
                    "SELECT * FROM step_evaluations WHERE run_id = ? ORDER BY timestamp_end DESC LIMIT ?",
                    (run_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM step_evaluations ORDER BY timestamp_end DESC LIMIT ?",
                    (limit,),
                )
            rows = []
            for r in cursor.fetchall():
                d = dict(r)
                if d.get("reasons_json"):
                    d["reasons"] = json.loads(d["reasons_json"])
                if d.get("metadata_json"):
                    d["metadata"] = json.loads(d["metadata_json"])
                rows.append(d)
            return rows

    def record_assurance_decision(self, decision: Any) -> None:
        """Record an assurance decision into the database."""
        d = decision.to_dict() if hasattr(decision, "to_dict") else dict(decision)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assurance_decisions (
                    decision_id, experiment_id, session_id, camera_profile,
                    step_id, sequence, decision, confidence, deviation_reason,
                    reason, reasons_json, evidence_summary_json,
                    recommended_recovery, severity, procedure_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    d.get("decision_id"),
                    d.get("experiment_id", "DEMO_EXP_001"),
                    d.get("session_id", "SESSION_001"),
                    d.get("camera_profile", "VIEW_LEFT"),
                    d.get("step_id"),
                    d.get("sequence", 1),
                    d.get("decision"),
                    d.get("confidence", 0.0),
                    d.get("deviation_reason"),
                    d.get("reason"),
                    json.dumps(d.get("reasons", [])),
                    json.dumps(d.get("evidence_summary", {})),
                    d.get("recommended_recovery"),
                    d.get("severity"),
                    d.get("procedure_version", "1.0.0"),
                ),
            )

    def get_assurance_decisions(
        self,
        session_id: Optional[str] = None,
        camera_profile: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query assurance decisions by session or camera profile."""
        with self.get_connection() as conn:
            query = "SELECT * FROM assurance_decisions"
            params: List[Any] = []
            clauses = []
            if session_id:
                clauses.append("session_id = ?")
                params.append(session_id)
            if camera_profile:
                clauses.append("camera_profile = ?")
                params.append(camera_profile.upper())
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, tuple(params))
            rows = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("reasons_json"):
                    item["reasons"] = json.loads(item["reasons_json"])
                if item.get("evidence_summary_json"):
                    item["evidence_summary"] = json.loads(item["evidence_summary_json"])
                rows.append(item)
            return rows

    def record_recovery_event(self, context: Any) -> None:
        """Record a closed-loop recovery event or state transition."""
        c = context.to_dict() if hasattr(context, "to_dict") else dict(context)
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO recovery_events (
                    context_id, session_id, step_id, deviation_reason,
                    state, explanation, recommendation, target_step_id,
                    detected_at, resolved_at, attempts, verified_corrective_action
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    c.get("context_id"),
                    c.get("session_id", "SESSION_001"),
                    c.get("step_id"),
                    c.get("deviation_reason"),
                    c.get("state"),
                    c.get("explanation"),
                    c.get("recommendation"),
                    c.get("target_step_id"),
                    c.get("detected_at", 0.0),
                    c.get("resolved_at"),
                    c.get("attempts", 1),
                    1 if c.get("verified_corrective_action") else 0,
                ),
            )

    def get_recovery_events(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Query recovery events."""
        with self.get_connection() as conn:
            if session_id:
                cursor = conn.execute(
                    "SELECT * FROM recovery_events WHERE session_id = ? ORDER BY detected_at DESC LIMIT ?",
                    (session_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM recovery_events ORDER BY detected_at DESC LIMIT ?",
                    (limit,),
                )
            return [dict(r) for r in cursor.fetchall()]

    def record_ui_audit_action(
        self,
        action_type: str,
        run_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an operator UI action that alters runtime state."""
        details_json = json.dumps(details) if details else None
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO ui_audit_events (run_id, action_type, details_json)
                VALUES (?, ?, ?)
                """,
                (run_id, action_type, details_json),
            )

    def get_ui_audit_actions(self, run_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Query operator UI actions."""
        with self.get_connection() as conn:
            if run_id:
                cursor = conn.execute(
                    "SELECT * FROM ui_audit_events WHERE run_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (run_id, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM ui_audit_events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                )
            return [dict(r) for r in cursor.fetchall()]



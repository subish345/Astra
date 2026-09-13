# ==============================================================================
# ASTRA-EA Ground Monitor State Model
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Reactive state store for Ground Monitor with Qt thread-safe signal synchronization."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from PySide6.QtCore import QObject, Signal

from streaming.events.schema import EventFilter, EventSeverity, EventType, GroundEvent, categorize_event


class GroundMonitorState(QObject):
    """Central presentation state reconstructed purely from received ground telemetry."""

    # Qt Signals for GUI reactivity
    sig_link_changed = Signal(dict)
    sig_mission_changed = Signal(str, str, str, str, int, int)
    sig_activity_changed = Signal(str)
    sig_assurance_changed = Signal(str, str)
    sig_alert_changed = Signal(str, str, str)  # (deviation, severity, recovery_action)
    sig_alert_ack_changed = Signal(str, str)   # (alert_id, lifecycle: RECEIVED / ACKNOWLEDGED / RESOLVED)
    sig_op_status_changed = Signal(str)        # NOMINAL / ATTENTION / DEGRADED / ANOMALY / RECOVERY / COMPLETE
    sig_reconciliation_changed = Signal(dict)  # {"last_seq": int, "missing_gaps": list, "is_synced": bool}
    sig_clocks_updated = Signal(float, str)    # (met_seconds, ground_receipt_utc)
    sig_timeline_added = Signal(object, float) # (event: GroundEvent, latency_ms: float)
    sig_health_changed = Signal(dict)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        # Connection state
        self.link_status: str = "OFFLINE"
        self.link_quality: str = "OFFLINE"
        self.video_connected: bool = False
        self.events_connected: bool = False
        self.heartbeat_age: float = 0.0
        self.stream_fps: float = 0.0
        self.reconnect_count: int = 0

        # Operational status & Reconciliation (Phase 19)
        self.operational_status: str = "NOMINAL"
        self.active_alert_id: Optional[str] = None
        self.alert_lifecycle: str = "RECEIVED"
        self.last_seen_seq: int = -1
        self.missing_gaps: List[Any] = []
        self.met_seconds: float = 0.0

        # Mission state
        self.experiment_id: str = "DEMO_EXP_001"
        self.run_id: str = "RUN_0001"
        self.current_step_id: str = "STEP_01"
        self.current_step_title: str = "Approach Station"
        self.step_index: int = 0
        self.total_steps: int = 4
        self.is_simulation: bool = False

        # Perception & Assurance state
        self.current_activity: str = "IDLE"
        self.assurance_decision: str = "UNCERTAIN"
        self.assurance_reason: str = "Awaiting Observation"
        self.active_deviation: Optional[str] = None
        self.recovery_action: Optional[str] = None

        # Telemetry & Timeline
        self.timeline_events: List[GroundEvent] = []
        self.health_metrics: Dict[str, Any] = {}

    def update_link(self, status_dict: Dict[str, Any]) -> None:
        """Update connection telemetry."""
        self.link_status = status_dict.get("overall", "OFFLINE")
        self.link_quality = status_dict.get("quality", "OFFLINE")
        self.video_connected = status_dict.get("video_connected", False)
        self.events_connected = status_dict.get("events_connected", False)
        self.heartbeat_age = status_dict.get("heartbeat_age_seconds", 0.0)
        self.stream_fps = status_dict.get("stream_fps", 0.0)
        self.reconnect_count = status_dict.get("reconnect_count", 0)

        self.sig_link_changed.emit(status_dict)

    def process_event(self, event: GroundEvent, latency_ms: float = 0.0) -> None:
        """Incorporate an incoming ground telemetry event into state."""
        self.timeline_events.append(event)
        self.sig_timeline_added.emit(event, latency_ms)

        if event.experiment_id:
            self.experiment_id = event.experiment_id
        if event.run_id:
            self.run_id = event.run_id

        # Detect simulation mode
        if "sim" in event.experiment_id.lower() or "sim" in event.run_id.lower() or event.payload.get("simulation_mode"):
            self.is_simulation = True

        # 1. Sequence gap detection (Section 44)
        seq = getattr(event, "sequence_num", None)
        if seq is not None:
            if self.last_seen_seq >= 0 and seq > self.last_seen_seq + 1:
                gap = (self.last_seen_seq + 1, seq - 1)
                self.missing_gaps.append(gap)
                self.sig_reconciliation_changed.emit({
                    "last_seq": seq,
                    "missing_gaps": self.missing_gaps,
                    "is_synced": False,
                })
            else:
                self.sig_reconciliation_changed.emit({
                    "last_seq": seq,
                    "missing_gaps": self.missing_gaps,
                    "is_synced": len(self.missing_gaps) == 0,
                })
            if seq > self.last_seen_seq:
                self.last_seen_seq = seq

        # 2. Process by event type
        if event.event_type == EventType.EXPERIMENT_STARTED:
            self.total_steps = event.payload.get("total_steps", 4)
            self.current_step_id = event.payload.get("first_step_id", "STEP_01")
            self.step_index = 0
            self.operational_status = "NOMINAL"
            self.sig_op_status_changed.emit(self.operational_status)
            self.sig_mission_changed.emit(
                self.experiment_id,
                self.run_id,
                self.current_step_id,
                self.current_step_title,
                self.step_index,
                self.total_steps,
            )

        elif event.event_type in (EventType.STEP_VERIFIED, EventType.STEP_UNCERTAIN):
            if event.step_id:
                self.current_step_id = event.step_id
            self.step_index = event.payload.get("step_index", self.step_index)
            if event.event_type == EventType.STEP_VERIFIED:
                self.assurance_decision = "VERIFIED"
                self.active_deviation = None
                self.recovery_action = None
                self.operational_status = "NOMINAL"
            else:
                self.assurance_decision = "UNCERTAIN"
                self.operational_status = "ATTENTION"

            self.sig_op_status_changed.emit(self.operational_status)
            self.assurance_reason = event.message
            self.sig_assurance_changed.emit(self.assurance_decision, self.assurance_reason)
            self.sig_mission_changed.emit(
                self.experiment_id,
                self.run_id,
                self.current_step_id,
                self.current_step_title,
                self.step_index,
                self.total_steps,
            )

        elif event.event_type == EventType.DEVIATION_DETECTED:
            self.assurance_decision = "DEVIATION"
            self.active_deviation = event.message or event.status or "DEVIATION DETECTED"
            self.recovery_action = event.payload.get("recovery_action", "Awaiting Recovery Directive")
            self.active_alert_id = event.event_id
            self.alert_lifecycle = "RECEIVED"
            self.operational_status = "ANOMALY"
            self.sig_op_status_changed.emit(self.operational_status)
            self.sig_assurance_changed.emit(self.assurance_decision, self.active_deviation)
            self.sig_alert_changed.emit(self.active_deviation, event.severity.value, self.recovery_action)
            self.sig_alert_ack_changed.emit(self.active_alert_id, self.alert_lifecycle)

        elif event.event_type == EventType.RECOVERY_REQUIRED:
            self.recovery_action = event.message or event.payload.get("recovery_action", "Execute Recovery")
            self.operational_status = "RECOVERY"
            self.sig_op_status_changed.emit(self.operational_status)
            self.sig_alert_changed.emit(self.active_deviation or "DEVIATION", event.severity.value, self.recovery_action)

        elif event.event_type == EventType.RECOVERY_VERIFIED:
            self.active_deviation = None
            self.recovery_action = None
            self.assurance_decision = "VERIFIED"
            self.assurance_reason = "Recovery Verified — Resumed Procedure"
            self.alert_lifecycle = "RESOLVED"
            self.operational_status = "NOMINAL"
            self.sig_op_status_changed.emit(self.operational_status)
            self.sig_assurance_changed.emit(self.assurance_decision, self.assurance_reason)
            self.sig_alert_changed.emit("", "INFO", "")
            self.sig_alert_ack_changed.emit(self.active_alert_id or "", self.alert_lifecycle)

        elif event.event_type == EventType.EXPERIMENT_COMPLETED:
            self.operational_status = "COMPLETE"
            self.sig_op_status_changed.emit(self.operational_status)

        elif event.event_type == EventType.SYSTEM_HEALTH_CHANGED:
            self.health_metrics.update(event.payload)
            self.sig_health_changed.emit(self.health_metrics)

        # Update activity if present in payload
        if "activity" in event.payload:
            self.current_activity = str(event.payload["activity"])
            self.sig_activity_changed.emit(self.current_activity)

    def acknowledge_active_alert(self, operator: str = "GROUND_OPERATOR") -> None:
        """Operator acknowledges active alert (Section 17: ACKNOWLEDGED does not mean RESOLVED)."""
        if self.active_deviation and self.alert_lifecycle != "RESOLVED":
            self.alert_lifecycle = "ACKNOWLEDGED"
            self.sig_alert_ack_changed.emit(self.active_alert_id or "DEV_ALERT", self.alert_lifecycle)

    def get_filtered_timeline(self, filter_type: EventFilter) -> List[GroundEvent]:
        """Return events matching the given filter."""
        if filter_type == EventFilter.ALL:
            return list(self.timeline_events)
        return [e for e in self.timeline_events if categorize_event(e.event_type) == filter_type]

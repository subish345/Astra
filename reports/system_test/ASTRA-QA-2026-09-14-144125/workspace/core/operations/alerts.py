"""Mission Alert System and Operator Escalation for ASTRA-EA (Phase 19, Section 15, 16, 17, 56, 57, D19.08).

Manages alert lifecycles (RECEIVED -> ACKNOWLEDGED -> RESOLVED), strict severity prioritization
(CRITICAL > WARNING > NOTICE > INFO), and tiered operational escalation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(str, Enum):
    """Operational alert urgency tiers (Section 15)."""
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertLifecycle(str, Enum):
    """Distinct lifecycle states of an operational alert (Section 17, 56)."""
    RECEIVED = "RECEIVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class EscalationLevel(str, Enum):
    """Tiered operational escalation levels (Section 57)."""
    LEVEL_1 = "LEVEL_1"  # Astronaut / Experiment Operator immediate response
    LEVEL_2 = "LEVEL_2"  # Ground System Engineer investigation
    LEVEL_3 = "LEVEL_3"  # Flight Director / Mission Authority disposition


# Numerical priority ordering for sorting (Section 16: CRITICAL > WARNING > NOTICE > INFO)
SEVERITY_WEIGHTS: Dict[AlertSeverity, int] = {
    AlertSeverity.CRITICAL: 4,
    AlertSeverity.WARNING: 3,
    AlertSeverity.NOTICE: 2,
    AlertSeverity.INFO: 1,
}


@dataclass
class MissionAlert:
    """Structured mission alert model with operator acknowledgement tracking."""
    alert_id: str
    severity: AlertSeverity
    source: str
    message: str
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mission_id: str = "DEMO_EXP_001"
    run_id: str = "RUN_0001"
    lifecycle_state: AlertLifecycle = AlertLifecycle.RECEIVED
    acknowledged_by: Optional[str] = None
    acknowledged_at_utc: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at_utc: Optional[str] = None
    resolution_notes: Optional[str] = None
    related_evidence_id: Optional[str] = None
    escalation_level: EscalationLevel = EscalationLevel.LEVEL_1

    def acknowledge(self, operator: str) -> None:
        """Operator marks alert as acknowledged (Section 17).

        Important: ACKNOWLEDGED does NOT mean RESOLVED.
        """
        if self.lifecycle_state == AlertLifecycle.RESOLVED:
            return
        self.lifecycle_state = AlertLifecycle.ACKNOWLEDGED
        self.acknowledged_by = operator
        self.acknowledged_at_utc = datetime.now(timezone.utc).isoformat()

    def resolve(self, operator: str, notes: str = "") -> None:
        """Operator or engineer closes alert once corrective action is confirmed."""
        self.lifecycle_state = AlertLifecycle.RESOLVED
        self.resolved_by = operator
        self.resolved_at_utc = datetime.now(timezone.utc).isoformat()
        self.resolution_notes = notes

    def escalate(self, target_level: EscalationLevel) -> None:
        """Escalate unresolved alert up the operational chain (Section 57)."""
        self.escalation_level = target_level

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["lifecycle_state"] = self.lifecycle_state.value
        d["escalation_level"] = self.escalation_level.value
        return d


class AlertManager:
    """Manages alert queue, prioritization, and acknowledgement lifecycle."""

    def __init__(self) -> None:
        self.alerts: List[MissionAlert] = []

    def post_alert(
        self,
        alert_id: str,
        severity: AlertSeverity,
        source: str,
        message: str,
        mission_id: str = "DEMO_EXP_001",
        run_id: str = "RUN_0001",
        related_evidence_id: Optional[str] = None,
        escalation_level: EscalationLevel = EscalationLevel.LEVEL_1,
    ) -> MissionAlert:
        """Post a new operational alert."""
        alert = MissionAlert(
            alert_id=alert_id,
            severity=severity,
            source=source,
            message=message,
            mission_id=mission_id,
            run_id=run_id,
            related_evidence_id=related_evidence_id,
            escalation_level=escalation_level,
        )
        self.alerts.append(alert)
        return alert

    def get_dominant_alert(self) -> Optional[MissionAlert]:
        """Return highest-priority un-resolved alert (Section 16).

        Only one primary critical event should visually dominate at a time.
        """
        unresolved = [a for a in self.alerts if a.lifecycle_state != AlertLifecycle.RESOLVED]
        if not unresolved:
            return None
        # Sort by severity weight descending, then timestamp
        return max(unresolved, key=lambda a: SEVERITY_WEIGHTS.get(a.severity, 0))

    def acknowledge_alert(self, alert_id: str, operator: str) -> bool:
        """Acknowledge an alert by ID."""
        for a in self.alerts:
            if a.alert_id == alert_id:
                a.acknowledge(operator)
                return True
        return False

    def resolve_alert(self, alert_id: str, operator: str, notes: str = "") -> bool:
        """Resolve an alert by ID."""
        for a in self.alerts:
            if a.alert_id == alert_id:
                a.resolve(operator, notes)
                return True
        return False

    def get_active_alerts(self) -> List[MissionAlert]:
        """All un-resolved alerts."""
        return [a for a in self.alerts if a.lifecycle_state != AlertLifecycle.RESOLVED]

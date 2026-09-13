"""Typed event contracts for ASTRA-EA mission telemetry and assurance logging.

All events are validated using Pydantic, enabling serialization to JSON for SQLite storage,
audit logs, and network transmission to the Ground Monitor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


def generate_event_id(prefix: str = "EVT") -> str:
    """Generate a unique event identifier with standardized prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:8].upper()}"


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class DecisionType(str, Enum):
    """Core tri-state assurance decision states."""
    VERIFIED = "VERIFIED"
    UNCERTAIN = "UNCERTAIN"
    DEVIATION = "DEVIATION"


class DeviationReason(str, Enum):
    """Reason classifications for procedural deviations."""
    SKIPPED_STEP = "SKIPPED_STEP"
    WRONG_ORDER = "WRONG_ORDER"
    WRONG_OBJECT = "WRONG_OBJECT"
    INCOMPLETE_ACTION = "INCOMPLETE_ACTION"
    UNEXPECTED_ACTION = "UNEXPECTED_ACTION"
    REPEATED_ACTION = "REPEATED_ACTION"
    TIMEOUT = "TIMEOUT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AssistantPriority(str, Enum):
    """Urgency level for astronaut guidance and voice notifications."""
    INFO = "INFO"
    GUIDANCE = "GUIDANCE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class HealthState(str, Enum):
    """Subsystem operational health status."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"


class BaseEvent(BaseModel):
    """Abstract base for all telemetry and mission events."""
    event_id: str = Field(default_factory=generate_event_id)
    timestamp: datetime = Field(default_factory=utc_now)
    run_id: Optional[str] = Field(default=None, description="Active experiment execution session ID")


class ProcedureDecision(BaseEvent):
    """Assurance engine evaluation output."""
    experiment_id: str
    step_id: str
    sequence: int
    decision: DecisionType
    deviation_reason: Optional[DeviationReason] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: Optional[str] = None
    evidence_id: Optional[str] = None


class ActivityEvent(BaseEvent):
    """Recognized physical activity event."""
    activity_name: str
    actor: str = "ASTRONAUT"
    object_id: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    evidence_ref: Optional[str] = None


class EvidenceEvent(BaseEvent):
    """Multimodal corroboration evidence bundle."""
    activity_ref: str
    evidence_score: float = Field(..., ge=0.0, le=1.0)
    items: Dict[str, Any] = Field(default_factory=dict)
    is_conclusive: bool = True


class AlertEvent(BaseEvent):
    """Notification emitted to astronaut via voice and GUI."""
    priority: AssistantPriority
    message: str
    spoken: bool = False
    cooldown_seconds: float = 3.5


class HealthEvent(BaseEvent):
    """Component health heartbeat or state change notification."""
    component: str
    state: HealthState
    metrics: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = None


class MissionEvent(BaseEvent):
    """High-level lifecycle event (START, PAUSE, RESUME, COMPLETE, ABORT)."""
    event_type: str
    experiment_id: str
    details: Dict[str, Any] = Field(default_factory=dict)

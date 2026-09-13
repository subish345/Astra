# ==============================================================================
# ASTRA-EA Ground Telemetry Event Schema
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Typed data schemas and serialization formats for lightweight ground telemetry events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Categorized ground telemetry event types."""
    EXPERIMENT_STARTED = "EXPERIMENT_STARTED"
    STEP_VERIFIED = "STEP_VERIFIED"
    STEP_UNCERTAIN = "STEP_UNCERTAIN"
    DEVIATION_DETECTED = "DEVIATION_DETECTED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    RECOVERY_VERIFIED = "RECOVERY_VERIFIED"
    EXPERIMENT_COMPLETED = "EXPERIMENT_COMPLETED"
    SYSTEM_HEALTH_CHANGED = "SYSTEM_HEALTH_CHANGED"
    CAMERA_STATUS_CHANGED = "CAMERA_STATUS_CHANGED"
    HEARTBEAT = "HEARTBEAT"
    TEST_EVENT = "TEST_EVENT"


class EventSeverity(str, Enum):
    """Event urgency and visual representation tier."""
    INFO = "INFO"
    WARNING = "WARNING"
    DANGER = "DANGER"


class EventFilter(str, Enum):
    """Ground timeline filtering categories."""
    ALL = "ALL"
    STEPS = "STEPS"
    DEVIATIONS = "DEVIATIONS"
    RECOVERY = "RECOVERY"
    SYSTEM = "SYSTEM"


def categorize_event(event_type: EventType) -> EventFilter:
    """Map an EventType to its corresponding UI timeline filter category."""
    if event_type in (EventType.STEP_VERIFIED, EventType.STEP_UNCERTAIN):
        return EventFilter.STEPS
    if event_type == EventType.DEVIATION_DETECTED:
        return EventFilter.DEVIATIONS
    if event_type in (EventType.RECOVERY_REQUIRED, EventType.RECOVERY_VERIFIED):
        return EventFilter.RECOVERY
    if event_type in (
        EventType.SYSTEM_HEALTH_CHANGED,
        EventType.CAMERA_STATUS_CHANGED,
        EventType.HEARTBEAT,
        EventType.EXPERIMENT_STARTED,
        EventType.EXPERIMENT_COMPLETED,
        EventType.TEST_EVENT,
    ):
        return EventFilter.SYSTEM
    return EventFilter.ALL


class GroundEvent(BaseModel):
    """Immutable, typed event model for remote ground telemetry and timeline display."""
    event_id: str = Field(..., description="Unique event identifier (e.g. EVT_00124)")
    sequence_num: int = Field(..., ge=0, description="Monotonic sequence number for gap detection and replay")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Onboard authoritative UTC timestamp (ISO 8601)",
    )
    experiment_id: str = Field(default="DEMO_EXP_001", description="Experiment procedure identifier")
    run_id: str = Field(default="RUN_0001", description="Mission execution session ID")
    event_type: EventType = Field(..., description="Telemetry event type")
    step_id: Optional[str] = Field(default=None, description="Associated experiment step ID")
    status: str = Field(default="", description="Operational status (VERIFIED, UNCERTAIN, DEVIATION, etc.)")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="Event severity tier")
    message: str = Field(default="", description="Human-readable event summary")
    correlation_id: Optional[str] = Field(default=None, description="Traceability correlation ID")
    evidence_id: Optional[str] = Field(default=None, description="Optional link to corroborating evidence bundle")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary typed metadata")

    def to_sse(self) -> str:
        """Format event as Server-Sent Event (SSE) wire payload."""
        data_json = self.model_dump_json()
        return f"id: {self.sequence_num}\nevent: {self.event_type.value}\ndata: {data_json}\n\n"

    @classmethod
    def from_json_str(cls, json_str: str) -> GroundEvent:
        """Parse GroundEvent from JSON string."""
        data = json.loads(json_str)
        return cls(**data)

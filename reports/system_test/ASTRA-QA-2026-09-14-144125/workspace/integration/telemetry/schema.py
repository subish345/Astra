"""Flight Telemetry Data Schemas for ASTRA-EA (Phase 18).

In accordance with Section 18 & 19:
Defines telemetry categories:
- HEALTH
- MISSION
- ASSURANCE
- PERFORMANCE
- FAULT
Preserves TBD fields for target spacecraft bus alignment.
"""

from __future__ import annotations

import enum
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class TelemetryCategory(str, enum.Enum):
    HEALTH = "HEALTH"
    MISSION = "MISSION"
    ASSURANCE = "ASSURANCE"
    PERFORMANCE = "PERFORMANCE"
    FAULT = "FAULT"


@dataclass
class HealthTelemetryPacket:
    """Subsystem hardware and component health telemetry."""
    timestamp_utc: str
    met_seconds: float
    camera_ok: bool
    model_ok: bool
    storage_ok: bool
    cpu_die_temp_c: Optional[float]
    gpu_die_temp_c: Optional[float]
    cpu_utilization_pct: float
    gpu_utilization_pct: float
    power_bus_voltage_v: Optional[float] = None  # TBD spacecraft bus probe
    subsystem_status: str = "READY"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MissionTelemetryPacket:
    """Experiment and procedure state telemetry."""
    timestamp_utc: str
    met_seconds: float
    experiment_id: str
    run_id: str
    current_step_id: str
    procedure_state: str  # INITIALIZING, IN_PROGRESS, PAUSED, COMPLETED, ABORTED
    step_elapsed_seconds: float
    total_steps: int
    completed_steps: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AssuranceTelemetryPacket:
    """Real-time assurance, deviation, and recovery state telemetry."""
    timestamp_utc: str
    met_seconds: float
    decision: str  # VERIFIED, UNCERTAIN, DEVIATION, PAUSED
    confidence: float
    deviation_type: Optional[str] = None
    recovery_active: bool = False
    recovery_instruction: Optional[str] = None
    evidence_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceTelemetryPacket:
    """Computational pipeline throughput and latency telemetry."""
    timestamp_utc: str
    met_seconds: float
    pipeline_fps: float
    inference_latency_ms: float
    end_to_end_latency_ms: float
    queue_depth: int
    memory_rss_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FaultTelemetryPacket:
    """Exception and anomaly notification telemetry."""
    timestamp_utc: str
    met_seconds: float
    fault_code: str
    subsystem: str
    severity: str  # WARNING, CRITICAL, FATAL
    message: str
    containment_action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

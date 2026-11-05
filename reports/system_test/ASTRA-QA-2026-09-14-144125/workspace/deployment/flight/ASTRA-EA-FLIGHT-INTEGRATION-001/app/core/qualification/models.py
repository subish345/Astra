"""Pydantic Data Models for ASTRA-EA Environmental & Hardware Qualification Program (Phase 17).

Standardized aerospace data structures for qualification baselines, test procedures,
telemetry records, and nonconformance management.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QualificationStatus(str, Enum):
    """Formal qualification status vocabulary (Section 3)."""
    PLANNED = "PLANNED"
    READY = "READY"
    NOT_PERFORMED = "NOT PERFORMED"
    IN_PROGRESS = "IN PROGRESS"
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    ABORTED = "ABORTED"
    WAIVED = "WAIVED"


class NCRSeverity(str, Enum):
    """Nonconformance severity taxonomy."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NCRStatus(str, Enum):
    """Nonconformance lifecycle status."""
    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
    RETEST = "RETEST"
    CLOSED = "CLOSED"
    WAIVED = "WAIVED"


class PowerState(str, Enum):
    """Software power failure response states (Section 25)."""
    POWER_NOMINAL = "POWER_NOMINAL"
    POWER_WARNING = "POWER_WARNING"
    POWER_CRITICAL = "POWER_CRITICAL"
    POWER_LOSS = "POWER_LOSS"
    POWER_RECOVERY = "POWER_RECOVERY"


class QualificationItem(BaseModel):
    """Formal Qualification Item Definition (Section 4)."""
    id: str = Field(..., description="Unique Qualification Item Identifier")
    hardware_version: str = Field(..., description="Hardware board/chassis revision")
    software_version: str = Field(default="1.0.0-RC1", description="Software version baseline")
    model_version: str = Field(default="yolov8n-astra-v1.0", description="Neural detector checkpoint version")
    configuration_version: str = Field(default="v1.0", description="Procedure configuration version")
    test_configuration: str = Field(default="QUAL-BENCH-COTS", description="Test harness configuration ID")
    serial_number: str = Field(default="ASTRA-SN-001", description="Hardware unit serial number")
    test_objective: str = Field(..., description="Primary qualification test objective")
    environment: str = Field(..., description="Target environmental stress domain")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Pass/fail criteria list")


class EnvironmentalSensorData(BaseModel):
    """Environmental chamber measurements (Section 38: Unknown values remain null)."""
    temperature_c: Optional[float] = None
    pressure_torr: Optional[float] = None
    acceleration_g_x: Optional[float] = None
    acceleration_g_y: Optional[float] = None
    acceleration_g_z: Optional[float] = None
    bus_voltage_v: Optional[float] = None
    bus_current_a: Optional[float] = None
    rf_field_v_m: Optional[float] = None
    radiation_dose_rad: Optional[float] = None


class SystemTelemetryData(BaseModel):
    """Software and compute health metrics synchronized with environment."""
    fps: Optional[float] = None
    latency_ms: Optional[float] = None
    cpu_utilization_percent: Optional[float] = None
    gpu_utilization_percent: Optional[float] = None
    ram_rss_mb: Optional[float] = None
    cpu_die_temp_c: Optional[float] = None
    gpu_die_temp_c: Optional[float] = None
    health_status: str = "NOMINAL"
    assurance_state: str = "IDLE"
    procedure_step: Optional[str] = None
    power_state: PowerState = PowerState.POWER_NOMINAL
    active_errors: List[str] = Field(default_factory=list)


class QualificationTelemetryFrame(BaseModel):
    """Standard Qualification Test Data Model (Section 38)."""
    qualification_id: str = Field(default="ASTRA-EA-QB-001")
    test_id: str = Field(...)
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    test_clock_seconds: float = Field(default_factory=time.monotonic)
    environment: EnvironmentalSensorData = Field(default_factory=EnvironmentalSensorData)
    system: SystemTelemetryData = Field(default_factory=SystemTelemetryData)


class TestProcedureSpec(BaseModel):
    """Standard Test Procedure Schema (Section 39)."""
    __test__ = False
    test_id: str
    objective: str
    configuration: str
    equipment: List[str]
    setup: List[str]
    instrumentation: List[str]
    preconditions: List[str]
    procedure: List[str]
    data_collection: List[str]
    acceptance_criteria: List[str]
    post_test_checks: List[str]
    failure_handling: List[str]
    status: QualificationStatus = QualificationStatus.PLANNED


class NonconformanceRecord(BaseModel):
    """Formal Nonconformance Record Schema (Section 43)."""
    ncr_id: str
    qualification_build_id: str = "ASTRA-EA-QB-001"
    test_id: str
    requirement_id: str
    severity: NCRSeverity
    date_opened: str
    originator: str
    failure_description: str
    root_cause: str
    corrective_action: str
    impact_analysis: Dict[str, Any] = Field(default_factory=dict)
    retest_id: Optional[str] = None
    disposition: str
    date_closed: Optional[str] = None
    status: NCRStatus

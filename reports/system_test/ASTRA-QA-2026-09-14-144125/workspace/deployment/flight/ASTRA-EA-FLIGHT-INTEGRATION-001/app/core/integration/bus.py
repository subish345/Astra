"""Spacecraft Vehicle Data Bus Interface Abstraction for ASTRA-EA (Phase 15).

Provides logical interface contracts for telemetry downlink, health reporting,
command ingestion, time synchronization, and power/thermal state adaptation.
"""

from __future__ import annotations

import enum
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional


class PowerState(str, enum.Enum):
    """Spacecraft host power bus condition."""
    POWER_ON = "POWER_ON"
    POWER_GOOD = "POWER_GOOD"
    POWER_DEGRADED = "POWER_DEGRADED"
    POWER_LOSS = "POWER_LOSS"
    POWER_RECOVERY = "POWER_RECOVERY"


class ThermalState(str, enum.Enum):
    """Spacecraft payload enclosure thermal status."""
    THERMAL_NORMAL = "THERMAL_NORMAL"
    THERMAL_WARNING = "THERMAL_WARNING"
    THERMAL_CRITICAL = "THERMAL_CRITICAL"


@dataclass
class VehicleTelemetryPacket:
    """Standardized 1Hz spacecraft downlink telemetry packet."""
    mission_id: str
    run_id: str
    scet_timestamp_iso: str
    monotonic_time_sec: float
    active_step_id: str
    assurance_state: str  # VERIFIED, UNCERTAIN, DEVIATION, PAUSED
    pipeline_fps: float
    latency_p95_ms: float
    health_mask: int  # Bitmask of healthy subsystems
    anomaly_flag: bool
    current_deviation: Optional[str] = None

    def serialize_json(self) -> str:
        """Serialize packet to standard JSON string."""
        return json.dumps(asdict(self))


@dataclass
class VehicleHealthReport:
    """Comprehensive payload subsystem health status report."""
    camera_ok: bool
    model_ok: bool
    assurance_ok: bool
    database_ok: bool
    storage_free_mb: float
    power_state: PowerState
    thermal_state: ThermalState
    chassis_temperature_c: float
    overall_health: str  # HEALTHY, DEGRADED, FAULT


class TimeSourceInterface:
    """Logical time source maintaining separation of monotonic duration and UTC."""

    def __init__(self):
        self._start_monotonic = time.monotonic()
        self._start_wall = time.time()

    def get_scet_timestamp_iso(self) -> str:
        """Get Spacecraft Event Time (SCET) in ISO-8601 UTC format."""
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int((time.time() % 1) * 1e6):06d}Z"

    def get_monotonic_duration_sec(self) -> float:
        """Get non-skewable hardware monotonic duration since startup."""
        return time.monotonic() - self._start_monotonic


class VehicleBusAdapter:
    """Abstract logical adapter for vehicle data bus communications."""

    def __init__(self, bus_id: str = "LOGICAL_SPACECRAFT_BUS_0"):
        self.bus_id = bus_id
        self.time_source = TimeSourceInterface()
        self.power_state = PowerState.POWER_GOOD
        self.thermal_state = ThermalState.THERMAL_NORMAL
        self._command_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register_command_handler(self, command_name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """Register handler for vehicle uplink commands."""
        self._command_handlers[command_name] = handler

    def dispatch_command(self, command_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch received vehicle command to registered handler."""
        if command_name not in self._command_handlers:
            return {"status": "ERROR", "message": f"Unrecognized command: {command_name}"}
        return self._command_handlers[command_name](payload)

    def publish_telemetry(self, packet: VehicleTelemetryPacket) -> bool:
        """Transmit telemetry packet onto vehicle data bus."""
        # Logical transmission simulation
        return True

    def update_power_state(self, new_state: PowerState) -> None:
        """Update host power rail state and adapt workload."""
        self.power_state = new_state

    def update_thermal_state(self, new_state: ThermalState) -> None:
        """Update chassis thermal state and adapt workload."""
        self.thermal_state = new_state

"""Unified Flight Software Health Model for ASTRA-EA (Phase 18).

In accordance with Section 49:
Aggregates subsystem health into system-level status: READY, DEGRADED, FAILED.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class HealthState(str, enum.Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass
class SubsystemHealth:
    name: str
    state: HealthState
    message: str = "Nominal"
    details: Dict[str, Any] = field(default_factory=dict)


class PlatformHealthMonitor:
    """Aggregates multi-subsystem operational health (Section 49)."""

    SUBSYSTEM_NAMES = [
        "BOOT",
        "PLATFORM",
        "CAMERA",
        "MODEL",
        "PERCEPTION",
        "PROCEDURE",
        "ASSURANCE",
        "STORAGE",
        "CLOCK",
        "TELEMETRY",
        "COMMAND",
    ]

    def __init__(self) -> None:
        self._subsystems: Dict[str, SubsystemHealth] = {
            name: SubsystemHealth(name=name, state=HealthState.READY)
            for name in self.SUBSYSTEM_NAMES
        }

    def update_subsystem(
        self,
        name: str,
        state: HealthState,
        message: str = "Nominal",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update single subsystem health."""
        if name in self._subsystems:
            self._subsystems[name].state = state
            self._subsystems[name].message = message
            if details:
                self._subsystems[name].details = details

    def get_subsystem(self, name: str) -> Optional[SubsystemHealth]:
        return self._subsystems.get(name)

    def evaluate_overall_health(self) -> HealthState:
        """Compute aggregate system health.

        Rules:
        - Any FAILED critical subsystem -> FAILED
        - Any DEGRADED subsystem -> DEGRADED
        - All READY -> READY
        """
        states = [s.state for s in self._subsystems.values()]
        if HealthState.FAILED in states:
            return HealthState.FAILED
        if HealthState.DEGRADED in states:
            return HealthState.DEGRADED
        return HealthState.READY

    def to_report(self) -> Dict[str, Any]:
        """Serialize full health status report."""
        overall = self.evaluate_overall_health()
        return {
            "overall_status": overall.value,
            "subsystems": {
                name: {
                    "state": s.state.value,
                    "message": s.message,
                    "details": s.details,
                }
                for name, s in self._subsystems.items()
            },
        }

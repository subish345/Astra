"""Unified Subsystem Health Aggregator for ASTRA-EA.

Aggregates operational status, heartbeats, and failure propagation across all
onboard subsystems, enforcing safety policies for critical vs non-critical failures.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from core.common.logging import get_logger

logger = get_logger("HEALTH")


class HealthStatus(str, Enum):
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    OFFLINE = "OFFLINE"


class SubsystemCriticality(str, Enum):
    CRITICAL = "CRITICAL"          # Mission must pause or halt if failed
    IMPORTANT = "IMPORTANT"        # System continues with degraded capabilities
    OPTIONAL = "OPTIONAL"          # Failure does not degrade core mission


SUBSYSTEM_CRITICALITY_MAP: Dict[str, SubsystemCriticality] = {
    "camera": SubsystemCriticality.CRITICAL,
    "perception": SubsystemCriticality.CRITICAL,
    "procedure": SubsystemCriticality.CRITICAL,
    "assurance": SubsystemCriticality.CRITICAL,
    "evidence": SubsystemCriticality.CRITICAL,
    "database": SubsystemCriticality.CRITICAL,
    "storage": SubsystemCriticality.IMPORTANT,
    "recording": SubsystemCriticality.IMPORTANT,
    "voice": SubsystemCriticality.OPTIONAL,
    "streaming": SubsystemCriticality.OPTIONAL,
    "ground_monitor": SubsystemCriticality.OPTIONAL,
}


class UnifiedHealthAggregator:
    """Aggregates heartbeats and evaluates operational status across all subsystems."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._last_evaluated: float = time.time()
        self._init_defaults()

    def _init_defaults(self) -> None:
        for name, crit in SUBSYSTEM_CRITICALITY_MAP.items():
            self._statuses[name] = {
                "status": HealthStatus.NORMAL.value,
                "criticality": crit.value,
                "message": "Initialized",
                "timestamp": time.time(),
            }

    def record_heartbeat(
        self,
        subsystem: str,
        status: HealthStatus | str,
        message: Optional[str] = None,
        telemetry: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record health update for a specific subsystem."""
        with self._lock:
            val = status.value if isinstance(status, HealthStatus) else str(status)
            crit = SUBSYSTEM_CRITICALITY_MAP.get(subsystem, SubsystemCriticality.OPTIONAL).value
            entry = {
                "status": val,
                "criticality": crit,
                "message": message or "Nominal",
                "timestamp": time.time(),
            }
            if telemetry:
                entry["telemetry"] = telemetry
            self._statuses[subsystem] = entry

    # Alias for update_component
    update_component = record_heartbeat

    def evaluate_system_health(self) -> Dict[str, Any]:
        """Compute top-level system health with failure propagation."""
        with self._lock:
            now = time.time()
            self._last_evaluated = now

            critical_failed: List[str] = []
            important_failed: List[str] = []
            any_degraded: List[str] = []

            for name, entry in self._statuses.items():
                st = entry["status"]
                crit = entry["criticality"]

                # Check stale heartbeat (>10s without update is degraded)
                age = now - entry["timestamp"]
                if age > 10.0 and st == HealthStatus.NORMAL.value:
                    st = HealthStatus.DEGRADED.value
                    entry["message"] = f"Heartbeat stale ({age:.1f}s)"

                if st == HealthStatus.FAILED.value:
                    if crit == SubsystemCriticality.CRITICAL.value:
                        critical_failed.append(name)
                    elif crit == SubsystemCriticality.IMPORTANT.value:
                        important_failed.append(name)
                elif st in (HealthStatus.DEGRADED.value, HealthStatus.OFFLINE.value):
                    if crit in (SubsystemCriticality.CRITICAL.value, SubsystemCriticality.IMPORTANT.value):
                        any_degraded.append(name)

            if critical_failed:
                overall = HealthStatus.FAILED
                summary_msg = f"Critical subsystems failed: {', '.join(critical_failed)}"
            elif important_failed or any_degraded:
                overall = HealthStatus.DEGRADED
                reasons = important_failed + any_degraded
                summary_msg = f"Degraded subsystems: {', '.join(reasons)}"
            else:
                overall = HealthStatus.NORMAL
                summary_msg = "All subsystems operational"

            return {
                "overall_status": overall.value,
                "summary": summary_msg,
                "timestamp": now,
                "critical_failures": critical_failed,
                "degraded_components": any_degraded,
                "subsystems": dict(self._statuses),
            }

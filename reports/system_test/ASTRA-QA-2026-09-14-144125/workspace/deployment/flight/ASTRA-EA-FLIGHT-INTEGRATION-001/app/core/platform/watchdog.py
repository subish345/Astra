"""Central Subsystem Watchdog and Fault Mitigation Engine for ASTRA-EA (Phase 18).

In accordance with Section 12 & 13:
Monitors periodic subsystem heartbeats (camera, perception, event bus, storage, mission state).
Evaluates configurable watchdog policies (WARN, RESTART_SUBSYSTEM, ENTER_DEGRADED, PAUSE_MISSION, SAFE_SHUTDOWN).
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


class WatchdogPolicy(str, enum.Enum):
    """Mitigation actions upon watchdog heartbeat timeout (Section 13)."""
    WARN = "WARN"
    RESTART_SUBSYSTEM = "RESTART_SUBSYSTEM"
    ENTER_DEGRADED = "ENTER_DEGRADED"
    PAUSE_MISSION = "PAUSE_MISSION"
    SAFE_SHUTDOWN = "SAFE_SHUTDOWN"


@dataclass
class SubsystemWatchdogEntry:
    name: str
    timeout_seconds: float
    last_heartbeat: float
    missed_count: int = 0
    is_healthy: bool = True
    last_action: Optional[WatchdogPolicy] = None


class Watchdog:
    """Central flight watchdog daemon (D18.10)."""

    def __init__(
        self,
        default_policy: WatchdogPolicy = WatchdogPolicy.ENTER_DEGRADED,
        default_timeout_seconds: float = 3.0,
    ) -> None:
        self.default_policy = default_policy
        self.default_timeout_seconds = default_timeout_seconds
        self.subsystems: Dict[str, SubsystemWatchdogEntry] = {}
        self._action_callbacks: Dict[WatchdogPolicy, List[Callable[[str], None]]] = {
            p: [] for p in WatchdogPolicy
        }

        # Auto-register core subsystems (Section 12)
        for s in ["main_process", "camera", "perception", "event_bus", "storage", "mission_state"]:
            self.register(s, timeout_seconds=default_timeout_seconds)

    def register(self, name: str, timeout_seconds: Optional[float] = None) -> None:
        """Register a subsystem under watchdog supervision."""
        timeout = timeout_seconds or self.default_timeout_seconds
        self.subsystems[name] = SubsystemWatchdogEntry(
            name=name,
            timeout_seconds=timeout,
            last_heartbeat=time.monotonic(),
        )

    def feed(self, name: str) -> bool:
        """Record heartbeat from a monitored subsystem."""
        if name not in self.subsystems:
            self.register(name)
        entry = self.subsystems[name]
        entry.last_heartbeat = time.monotonic()
        entry.missed_count = 0
        entry.is_healthy = True
        return True

    def register_action_handler(
        self,
        policy: WatchdogPolicy,
        handler: Callable[[str], None],
    ) -> None:
        """Register callback for when a specific policy action is triggered."""
        self._action_callbacks[policy].append(handler)

    def check(self) -> Dict[str, Any]:
        """Audit all subsystems against their timeout deadlines."""
        now = time.monotonic()
        all_healthy = True
        degraded = []
        triggered_actions = []

        for name, entry in self.subsystems.items():
            dt = now - entry.last_heartbeat
            if dt > entry.timeout_seconds:
                entry.missed_count += 1
                entry.is_healthy = False
                all_healthy = False
                degraded.append(name)
                entry.last_action = self.default_policy

                # Dispatch callbacks
                for cb in self._action_callbacks[self.default_policy]:
                    try:
                        cb(name)
                    except Exception:
                        pass

                triggered_actions.append({
                    "subsystem": name,
                    "elapsed_seconds": round(dt, 2),
                    "action": self.default_policy.value,
                })

        return {
            "all_healthy": all_healthy,
            "monitored_count": len(self.subsystems),
            "unhealthy_subsystems": degraded,
            "triggered_actions": triggered_actions,
        }

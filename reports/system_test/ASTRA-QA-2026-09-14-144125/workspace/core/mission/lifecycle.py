"""Authoritative Mission Lifecycle State Machine for ASTRA-EA.

Centralizes global mission execution states, prevents fragmented subsystem status,
and enforces valid state transition topologies across Onboard Core, Mission Console,
and Ground Monitor.
"""

from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Callable, Dict, List, Optional, Set

from core.common.logging import get_logger

logger = get_logger("LIFECYCLE")


class MissionLifecycleState(str, Enum):
    """Authoritative mission lifecycle states."""
    BOOT = "BOOT"
    INITIALIZING = "INITIALIZING"
    SELF_TEST = "SELF_TEST"
    READY = "READY"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DEGRADED = "DEGRADED"
    RECOVERY = "RECOVERY"
    COMPLETING = "COMPLETING"
    COMPLETED = "COMPLETED"
    ABORTING = "ABORTING"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"


# Allowable transition topology
VALID_TRANSITIONS: Dict[MissionLifecycleState, Set[MissionLifecycleState]] = {
    MissionLifecycleState.BOOT: {
        MissionLifecycleState.INITIALIZING,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.INITIALIZING: {
        MissionLifecycleState.SELF_TEST,
        MissionLifecycleState.FAILED,
        MissionLifecycleState.SHUTTING_DOWN,
    },
    MissionLifecycleState.SELF_TEST: {
        MissionLifecycleState.READY,
        MissionLifecycleState.DEGRADED,
        MissionLifecycleState.FAILED,
        MissionLifecycleState.SHUTTING_DOWN,
    },
    MissionLifecycleState.READY: {
        MissionLifecycleState.STARTING,
        MissionLifecycleState.SELF_TEST,
        MissionLifecycleState.SHUTTING_DOWN,
        MissionLifecycleState.STOPPED,
    },
    MissionLifecycleState.STARTING: {
        MissionLifecycleState.RUNNING,
        MissionLifecycleState.FAILED,
        MissionLifecycleState.ABORTING,
    },
    MissionLifecycleState.RUNNING: {
        MissionLifecycleState.PAUSED,
        MissionLifecycleState.DEGRADED,
        MissionLifecycleState.RECOVERY,
        MissionLifecycleState.COMPLETING,
        MissionLifecycleState.ABORTING,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.PAUSED: {
        MissionLifecycleState.RUNNING,
        MissionLifecycleState.ABORTING,
        MissionLifecycleState.SHUTTING_DOWN,
    },
    MissionLifecycleState.DEGRADED: {
        MissionLifecycleState.STARTING,
        MissionLifecycleState.RUNNING,
        MissionLifecycleState.PAUSED,
        MissionLifecycleState.RECOVERY,
        MissionLifecycleState.COMPLETING,
        MissionLifecycleState.ABORTING,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.RECOVERY: {
        MissionLifecycleState.RUNNING,
        MissionLifecycleState.DEGRADED,
        MissionLifecycleState.ABORTING,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.COMPLETING: {
        MissionLifecycleState.COMPLETED,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.COMPLETED: {
        MissionLifecycleState.READY,
        MissionLifecycleState.SHUTTING_DOWN,
        MissionLifecycleState.STOPPED,
    },
    MissionLifecycleState.ABORTING: {
        MissionLifecycleState.ABORTED,
        MissionLifecycleState.FAILED,
    },
    MissionLifecycleState.ABORTED: {
        MissionLifecycleState.READY,
        MissionLifecycleState.SHUTTING_DOWN,
        MissionLifecycleState.STOPPED,
    },
    MissionLifecycleState.FAILED: {
        MissionLifecycleState.READY,
        MissionLifecycleState.SHUTTING_DOWN,
        MissionLifecycleState.STOPPED,
    },
    MissionLifecycleState.SHUTTING_DOWN: {
        MissionLifecycleState.STOPPED,
    },
    MissionLifecycleState.STOPPED: {
        MissionLifecycleState.BOOT,
        MissionLifecycleState.INITIALIZING,
    },
}


class MissionLifecycleManager:
    """Thread-safe state machine managing mission lifecycle."""

    def __init__(self, initial_state: MissionLifecycleState = MissionLifecycleState.BOOT) -> None:
        self._current_state: MissionLifecycleState = initial_state
        self._lock = threading.RLock()
        self._listeners: List[Callable[[MissionLifecycleState, MissionLifecycleState, Optional[str]], None]] = []
        self._history: List[Dict[str, Any]] = [
            {
                "from_state": None,
                "to_state": initial_state.value,
                "timestamp": time.time(),
                "reason": "Initial boot",
            }
        ]

    @property
    def current_state(self) -> MissionLifecycleState:
        with self._lock:
            return self._current_state

    @property
    def state(self) -> MissionLifecycleState:
        """Alias for current_state."""
        with self._lock:
            return self._current_state

    def is_active(self) -> bool:
        """Return whether mission is actively running, degraded, or in recovery."""
        with self._lock:
            return self._current_state in (
                MissionLifecycleState.RUNNING,
                MissionLifecycleState.DEGRADED,
                MissionLifecycleState.RECOVERY,
            )

    def add_listener(
        self,
        callback: Callable[[MissionLifecycleState, MissionLifecycleState, Optional[str]], None],
    ) -> None:
        """Register a callback invoked on state transitions."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def transition_to(
        self,
        new_state: MissionLifecycleState,
        reason: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """Attempt transition to a new lifecycle state."""
        with self._lock:
            prev_state = self._current_state
            if prev_state == new_state:
                return True

            valid_targets = VALID_TRANSITIONS.get(prev_state, set())
            if not force and new_state not in valid_targets:
                logger.warning(
                    "Invalid lifecycle transition rejected: %s -> %s (Reason: %s)",
                    prev_state.value,
                    new_state.value,
                    reason,
                )
                return False

            self._current_state = new_state
            record = {
                "from_state": prev_state.value,
                "to_state": new_state.value,
                "timestamp": time.time(),
                "reason": reason,
            }
            self._history.append(record)
            logger.info("Lifecycle transition: %s -> %s (%s)", prev_state.value, new_state.value, reason or "Nominal")

            # Notify listeners outside lock
            callbacks = list(self._listeners)

        for cb in callbacks:
            try:
                cb(prev_state, new_state, reason)
            except Exception as e:
                logger.error("Error in lifecycle state listener: %s", e)

        return True

    def get_history(self) -> List[Dict[str, Any]]:
        """Return audit trail of lifecycle transitions."""
        with self._lock:
            return list(self._history)

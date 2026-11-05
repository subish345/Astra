"""Subsystem health monitoring manager for ASTRA-EA.

Tracks heartbeats, resource metrics, degradation states, and failure recovery
across all application subsystems.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from core.common.logging import get_logger
from core.health.types import ComponentHealth, HealthComponent, HealthState
from core.mission.events import HealthEvent

logger = get_logger("HEALTH")


class HealthManager:
    """Central registry and evaluator of system subsystem health."""

    def __init__(self, on_health_changed: Optional[Callable[[HealthEvent], None]] = None):
        self._components: Dict[HealthComponent, ComponentHealth] = {}
        self.on_health_changed = on_health_changed

        # Register default core components
        for comp in HealthComponent:
            self.register_component(comp)

    def register_component(self, component: HealthComponent) -> None:
        """Register a subsystem for health monitoring."""
        if component not in self._components:
            self._components[component] = ComponentHealth(component=component)

    def heartbeat(
        self,
        component: HealthComponent,
        state: HealthState = HealthState.NORMAL,
        metrics: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> HealthEvent:
        """Record a component heartbeat and detect status transitions."""
        if component not in self._components:
            self.register_component(component)

        comp_health = self._components[component]
        previous_state = comp_health.state

        comp_health.state = state
        comp_health.last_heartbeat = datetime.now(timezone.utc)
        comp_health.metrics = metrics or {}
        comp_health.message = message

        event = HealthEvent(
            component=component.value,
            state=state,
            metrics=comp_health.metrics,
            message=message,
        )

        if previous_state != state:
            log_fn = logger.warning if state in (HealthState.DEGRADED, HealthState.FAILED) else logger.info
            log_fn("Subsystem [%s] state transition: %s -> %s (%s)", component.value, previous_state.value, state.value, message or "N/A")
            if self.on_health_changed:
                try:
                    self.on_health_changed(event)
                except Exception as exc:
                    logger.error("Error in health change callback: %s", exc)

        return event

    def get_component_health(self, component: HealthComponent) -> ComponentHealth:
        """Fetch current telemetry for a specific subsystem."""
        return self._components.get(component, ComponentHealth(component=component, state=HealthState.FAILED, message="Unregistered"))

    def get_all_health(self) -> Dict[str, ComponentHealth]:
        """Return a mapping of all registered component statuses."""
        return {k.value: v for k, v in self._components.items()}

    def get_overall_health(self) -> HealthState:
        """Evaluate system-wide operational health.

        Rules:
        - If any critical component (CAMERA, PERCEPTION, PROCEDURE, ASSURANCE, DATABASE) is FAILED -> FAILED
        - If auxiliary component (VOICE, STREAMING) is FAILED -> DEGRADED
        - If any component is DEGRADED -> DEGRADED
        - Otherwise -> NORMAL
        """
        critical_components = {
            HealthComponent.CAMERA,
            HealthComponent.PERCEPTION,
            HealthComponent.PROCEDURE,
            HealthComponent.ASSURANCE,
            HealthComponent.DATABASE,
        }

        has_degraded = False

        for comp, health in self._components.items():
            if health.state == HealthState.FAILED:
                if comp in critical_components:
                    return HealthState.FAILED
                else:
                    has_degraded = True
            elif health.state == HealthState.DEGRADED:
                has_degraded = True

        return HealthState.DEGRADED if has_degraded else HealthState.NORMAL

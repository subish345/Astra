"""Subsystem health monitoring data types for ASTRA-EA.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from core.mission.events import HealthState


class HealthComponent(str, Enum):
    """Subsystems monitored by the ASTRA-EA health system."""
    CAMERA = "CAMERA"
    PERCEPTION = "PERCEPTION"
    PROCEDURE = "PROCEDURE"
    ASSURANCE = "ASSURANCE"
    ASSISTANCE = "ASSISTANCE"
    DATABASE = "DATABASE"
    STORAGE = "STORAGE"
    VOICE = "VOICE"
    STREAMING = "STREAMING"
    SYSTEM = "SYSTEM"


@dataclass
class ComponentHealth:
    """Telemetry status of an individual subsystem component."""
    component: HealthComponent
    state: HealthState = HealthState.NORMAL
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None

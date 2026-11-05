"""Flight Telemetry Interface and Publisher Base for ASTRA-EA (Phase 18).

In accordance with Section 18 & 20:
Provides abstract telemetry publisher interface with configurable rates.
Preserves TBD rate defaults pending target spacecraft program specification.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, Optional

from integration.telemetry.schema import (
    AssuranceTelemetryPacket,
    FaultTelemetryPacket,
    HealthTelemetryPacket,
    MissionTelemetryPacket,
    PerformanceTelemetryPacket,
)


class TelemetryPublisher(abc.ABC):
    """Abstract Telemetry Publisher (D18.07)."""

    def __init__(
        self,
        health_interval_s: float = 1.0,       # TBD default 1 Hz
        mission_interval_s: float = 1.0,      # TBD default 1 Hz
        performance_interval_s: float = 2.0,  # TBD default 0.5 Hz
    ) -> None:
        self.health_interval_s = health_interval_s
        self.mission_interval_s = mission_interval_s
        self.performance_interval_s = performance_interval_s
        self.is_connected: bool = True

    @abc.abstractmethod
    def publish_health(self, packet: HealthTelemetryPacket) -> bool:
        """Publish health telemetry packet."""
        pass

    @abc.abstractmethod
    def publish_mission(self, packet: MissionTelemetryPacket) -> bool:
        """Publish mission telemetry packet."""
        pass

    @abc.abstractmethod
    def publish_assurance(self, packet: AssuranceTelemetryPacket) -> bool:
        """Publish assurance decision telemetry packet."""
        pass

    @abc.abstractmethod
    def publish_performance(self, packet: PerformanceTelemetryPacket) -> bool:
        """Publish computational performance telemetry packet."""
        pass

    @abc.abstractmethod
    def publish_fault(self, packet: FaultTelemetryPacket) -> bool:
        """Publish fault notification telemetry packet."""
        pass

"""Concrete Flight Telemetry Publishers for ASTRA-EA (Phase 18)."""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from integration.telemetry.interface import TelemetryPublisher
from integration.telemetry.schema import (
    AssuranceTelemetryPacket,
    FaultTelemetryPacket,
    HealthTelemetryPacket,
    MissionTelemetryPacket,
    PerformanceTelemetryPacket,
)

logger = logging.getLogger("telemetry_publisher")


class FileTelemetryPublisher(TelemetryPublisher):
    """Logs telemetry packets to structured NDJSON files in flight_data/telemetry/."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        health_interval_s: float = 1.0,
        mission_interval_s: float = 1.0,
        performance_interval_s: float = 2.0,
    ) -> None:
        super().__init__(health_interval_s, mission_interval_s, performance_interval_s)
        self.output_dir = output_dir or Path("flight_data/telemetry")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._telemetry_log_file = self.output_dir / "flight_telemetry.ndjson"

    def _append_record(self, category: str, data: Dict[str, Any]) -> bool:
        if not self.is_connected:
            # Section 46: Telemetry degraded on channel loss, but pipeline does not crash
            return False
        record = {
            "telemetry_category": category,
            **data,
        }
        try:
            with open(self._telemetry_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            return True
        except Exception as e:
            logger.warning("Failed to write telemetry record: %s", e)
            return False

    def publish_health(self, packet: HealthTelemetryPacket) -> bool:
        return self._append_record("HEALTH", packet.to_dict())

    def publish_mission(self, packet: MissionTelemetryPacket) -> bool:
        return self._append_record("MISSION", packet.to_dict())

    def publish_assurance(self, packet: AssuranceTelemetryPacket) -> bool:
        return self._append_record("ASSURANCE", packet.to_dict())

    def publish_performance(self, packet: PerformanceTelemetryPacket) -> bool:
        return self._append_record("PERFORMANCE", packet.to_dict())

    def publish_fault(self, packet: FaultTelemetryPacket) -> bool:
        return self._append_record("FAULT", packet.to_dict())


class MemoryTelemetryPublisher(TelemetryPublisher):
    """In-memory telemetry queue for HIL and unit test scenarios."""

    def __init__(
        self,
        max_depth: int = 1000,
        health_interval_s: float = 1.0,
        mission_interval_s: float = 1.0,
        performance_interval_s: float = 2.0,
    ) -> None:
        super().__init__(health_interval_s, mission_interval_s, performance_interval_s)
        self.packets: Deque[Dict[str, Any]] = deque(maxlen=max_depth)

    def _store(self, category: str, data: Dict[str, Any]) -> bool:
        if not self.is_connected:
            return False
        self.packets.append({"category": category, **data})
        return True

    def publish_health(self, packet: HealthTelemetryPacket) -> bool:
        return self._store("HEALTH", packet.to_dict())

    def publish_mission(self, packet: MissionTelemetryPacket) -> bool:
        return self._store("MISSION", packet.to_dict())

    def publish_assurance(self, packet: AssuranceTelemetryPacket) -> bool:
        return self._store("ASSURANCE", packet.to_dict())

    def publish_performance(self, packet: PerformanceTelemetryPacket) -> bool:
        return self._store("PERFORMANCE", packet.to_dict())

    def publish_fault(self, packet: FaultTelemetryPacket) -> bool:
        return self._store("FAULT", packet.to_dict())

    def get_packets(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if category is None:
            return list(self.packets)
        return [p for p in self.packets if p.get("category") == category]

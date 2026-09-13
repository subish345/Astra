"""Generic Qualification Telemetry Interface & Time Synchronization Engine for ASTRA-EA (Phase 17).

Provides synchronized multi-channel ingestion of external chamber sensors and internal
system performance metrics. Complies with ECSS-E-ST-10-03C telemetry standards.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import psutil

from core.qualification.models import (
    EnvironmentalSensorData,
    PowerState,
    QualificationTelemetryFrame,
    SystemTelemetryData,
)

logger = logging.getLogger("qualification_telemetry")


class QualificationTelemetry:
    """Standard qualification telemetry provider and chamber sync daemon.

    Correlates environmental chamber conditions (temperature, pressure, voltage, vibration)
    with onboard software assurance health (FPS, latency, procedure step, error flags).
    """

    def __init__(
        self,
        test_id: str = "QUAL-TEST-001",
        qualification_id: str = "ASTRA-EA-QB-001",
        log_dir: Optional[Path] = None,
    ):
        self.test_id = test_id
        self.qualification_id = qualification_id
        self.log_dir = log_dir or Path("qualification/evidence/telemetry")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Time synchronization offsets
        self.test_clock_epoch = time.monotonic()
        self.instrument_clock_offset_ms = 0.0

        # Environmental sensor callback hooks (connected during facility tests)
        self._environmental_provider: Optional[Callable[[], EnvironmentalSensorData]] = None

        # Internal state tracking
        self.current_power_state = PowerState.POWER_NOMINAL
        self.current_procedure_step: Optional[str] = None
        self.current_assurance_state: str = "IDLE"
        self.last_fps: float = 30.0
        self.last_latency_ms: float = 25.0
        self.active_errors: List[str] = []

    def set_environmental_provider(self, provider: Callable[[], EnvironmentalSensorData]) -> None:
        """Register external chamber instrumentation sensor callback."""
        self._environmental_provider = provider

    def set_time_sync(self, master_chamber_time_s: float) -> None:
        """Synchronize external chamber master clock with local monotonic clock."""
        local_time_s = time.monotonic()
        self.instrument_clock_offset_ms = (master_chamber_time_s - local_time_s) * 1000.0
        logger.info("Time sync calibrated. Offset: %.2f ms", self.instrument_clock_offset_ms)

    def update_system_state(
        self,
        fps: Optional[float] = None,
        latency_ms: Optional[float] = None,
        procedure_step: Optional[str] = None,
        assurance_state: Optional[str] = None,
        power_state: Optional[PowerState] = None,
        error: Optional[str] = None,
    ) -> None:
        """Update active software health attributes from the core pipeline."""
        if fps is not None:
            self.last_fps = fps
        if latency_ms is not None:
            self.last_latency_ms = latency_ms
        if procedure_step is not None:
            self.current_procedure_step = procedure_step
        if assurance_state is not None:
            self.current_assurance_state = assurance_state
        if power_state is not None:
            self.current_power_state = power_state
        if error:
            self.active_errors.append(error)

    def capture_frame(
        self,
        manual_env: Optional[Dict[str, Any]] = None,
    ) -> QualificationTelemetryFrame:
        """Capture an instantaneous synchronized telemetry frame."""
        # 1. Read environmental data
        if self._environmental_provider:
            try:
                env_data = self._environmental_provider()
            except Exception as e:
                logger.warning("Error querying external chamber sensor: %s", e)
                env_data = EnvironmentalSensorData()
        elif manual_env:
            env_data = EnvironmentalSensorData(**manual_env)
        else:
            # All uninstrumented environmental channels remain null (Section 38 rule)
            env_data = EnvironmentalSensorData()

        # 2. Read live OS and compute resources
        proc = psutil.Process()
        cpu_pct = psutil.cpu_percent(interval=None)
        mem_rss_mb = proc.memory_info().rss / (1024.0 * 1024.0)

        # Silicon die temperature where available via Linux thermal sysfs
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for k, v in temps.items():
                    if v:
                        cpu_temp = v[0].current
                        break
        except Exception:
            pass

        sys_data = SystemTelemetryData(
            fps=self.last_fps,
            latency_ms=self.last_latency_ms,
            cpu_utilization_percent=cpu_pct,
            ram_rss_mb=round(mem_rss_mb, 1),
            cpu_die_temp_c=cpu_temp,
            health_status="DEGRADED" if self.active_errors else "NOMINAL",
            assurance_state=self.current_assurance_state,
            procedure_step=self.current_procedure_step,
            power_state=self.current_power_state,
            active_errors=list(self.active_errors),
        )

        return QualificationTelemetryFrame(
            qualification_id=self.qualification_id,
            test_id=self.test_id,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            test_clock_seconds=round(time.monotonic() - self.test_clock_epoch, 3),
            environment=env_data,
            system=sys_data,
        )

    def log_frame(self, frame: QualificationTelemetryFrame) -> Path:
        """Append frame to NDJSON qualification telemetry log."""
        out_path = self.log_dir / f"{self.test_id}_telemetry.ndjson"
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(frame.model_dump_json() + "\n")
        return out_path

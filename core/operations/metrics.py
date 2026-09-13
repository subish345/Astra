"""Operational Metrics and KPI Engine for ASTRA-EA (Phase 19, Section 58, 59, D19.21).

Tracks mission timing benchmarks (startup, preparation, experiment, deviation response, recovery,
reconnect, report generation) and computes operational KPIs for post-mission engineering review.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class OperationalTimings:
    """Durations and latency timestamps for operational workflows (Section 58)."""
    startup_time_seconds: float = 0.0
    preparation_time_seconds: float = 0.0
    experiment_duration_seconds: float = 0.0
    mean_deviation_response_seconds: float = 0.0
    mean_recovery_seconds: float = 0.0
    ground_reconnect_seconds: float = 0.0
    report_generation_seconds: float = 0.0
    operator_mistakes_count: int = 0


@dataclass
class OperationalKPIs:
    """High-level operational performance indicators (Section 59)."""
    mission_success: bool = True
    steps_total: int = 4
    steps_verified: int = 4
    step_verification_rate: float = 100.0
    deviations_count: int = 0
    recoveries_count: int = 0
    recovery_success_rate: float = 100.0
    uncertainty_count: int = 0
    operator_interventions: int = 0
    system_downtime_seconds: float = 0.0
    network_downtime_seconds: float = 0.0


class OperationalMetricsTracker:
    """Collects timestamps and events during a run to calculate mission timings and KPIs."""

    def __init__(self, run_id: str = "RUN_0001") -> None:
        self.run_id = run_id
        self.timings = OperationalTimings()
        self.kpis = OperationalKPIs()
        self._deviation_timestamps: List[float] = []
        self._recovery_timestamps: List[float] = []

    def record_startup_duration(self, seconds: float) -> None:
        self.timings.startup_time_seconds = round(seconds, 3)

    def record_preparation_duration(self, seconds: float) -> None:
        self.timings.preparation_time_seconds = round(seconds, 3)

    def record_experiment_duration(self, seconds: float) -> None:
        self.timings.experiment_duration_seconds = round(seconds, 3)

    def record_deviation(self, deviation_time_s: float) -> None:
        self._deviation_timestamps.append(deviation_time_s)
        self.kpis.deviations_count += 1

    def record_recovery(self, recovery_time_s: float) -> None:
        self._recovery_timestamps.append(recovery_time_s)
        self.kpis.recoveries_count += 1
        if self._deviation_timestamps:
            delta = recovery_time_s - self._deviation_timestamps[-1]
            self.timings.mean_recovery_seconds = round(delta, 3)

    def record_operator_mistake(self) -> None:
        self.timings.operator_mistakes_count += 1
        self.kpis.operator_interventions += 1

    def compute_summary(self) -> Dict[str, Any]:
        """Aggregate operational KPIs and timings into report structure."""
        if self.kpis.steps_total > 0:
            self.kpis.step_verification_rate = round(
                (self.kpis.steps_verified / self.kpis.steps_total) * 100.0, 1
            )
        if self.kpis.deviations_count > 0:
            self.kpis.recovery_success_rate = round(
                (self.kpis.recoveries_count / self.kpis.deviations_count) * 100.0, 1
            )
            self.kpis.mission_success = self.kpis.recoveries_count == self.kpis.deviations_count
        else:
            self.kpis.recovery_success_rate = 100.0
            self.kpis.mission_success = True

        return {
            "run_id": self.run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "timings": asdict(self.timings),
            "kpis": asdict(self.kpis),
        }

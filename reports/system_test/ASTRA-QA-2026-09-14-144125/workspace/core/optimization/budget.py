"""Runtime Resource Budget and Degraded Mode Controller for ASTRA-EA.

Enforces operational resource ceilings:
- Maximum process RSS memory (GB)
- Maximum GPU VRAM consumption (GB)
- Maximum CPU utilization (%)
- Maximum queue depth before backpressure

When resource budgets are breached, the controller engages DEGRADED mode,
adapting non-critical background frequencies (pose/hands, stream bitrate) while
strictly preserving critical experiment procedure assurance and local logging.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import psutil

from core.common.logging import get_logger
from core.optimization.backend import ComputeBackend, PlatformInspector

logger = get_logger("OPTIMIZATION")


@dataclass
class ResourceBudget:
    """Configurable operational resource limits."""
    max_ram_gb: float = 4.0
    max_gpu_memory_gb: float = 6.0
    max_cpu_percent: float = 85.0
    max_queue_size: int = 5


class BudgetMonitor:
    """Tracks resource consumption against configured budget ceilings."""

    def __init__(
        self,
        budget: Optional[ResourceBudget] = None,
        backend: Optional[ComputeBackend] = None,
    ) -> None:
        self.budget = budget or ResourceBudget()
        self.backend = backend or PlatformInspector.create_backend()
        self.process = psutil.Process(os.getpid())

        self._is_degraded: bool = False
        self._violations: List[str] = []

    @property
    def is_degraded(self) -> bool:
        return self._is_degraded

    @property
    def violations(self) -> List[str]:
        return list(self._violations)

    def check_limits(self, current_queue_size: int = 0) -> Dict[str, Any]:
        """Check system usage against budget and update degraded state."""
        mem_rss_gb = self.process.memory_info().rss / (1024**3)
        cpu_pct = self.process.cpu_percent()

        mem_info = self.backend.memory_info()
        vram_used_mb = mem_info.get("vram_used_mb")
        vram_used_gb = (vram_used_mb / 1024.0) if vram_used_mb is not None else 0.0

        violations: List[str] = []

        if mem_rss_gb > self.budget.max_ram_gb:
            violations.append(f"RAM exceeded: {mem_rss_gb:.2f} GB > {self.budget.max_ram_gb} GB")

        if vram_used_gb > self.budget.max_gpu_memory_gb:
            violations.append(f"VRAM exceeded: {vram_used_gb:.2f} GB > {self.budget.max_gpu_memory_gb} GB")

        if cpu_pct > self.budget.max_cpu_percent:
            violations.append(f"CPU exceeded: {cpu_pct:.1f}% > {self.budget.max_cpu_percent}%")

        if current_queue_size > self.budget.max_queue_size:
            violations.append(f"Queue backpressure: {current_queue_size} > {self.budget.max_queue_size}")

        self._violations = violations
        was_degraded = self._is_degraded
        self._is_degraded = len(violations) > 0

        if self._is_degraded and not was_degraded:
            logger.warning("Resource budget breached! Engaging DEGRADED mode: %s", violations)
        elif not self._is_degraded and was_degraded:
            logger.info("Resource levels restored. Exiting DEGRADED mode.")

        return {
            "status": "DEGRADED" if self._is_degraded else "NOMINAL",
            "violations": violations,
            "metrics": {
                "process_ram_gb": round(mem_rss_gb, 3),
                "process_cpu_percent": round(cpu_pct, 1),
                "gpu_vram_gb": round(vram_used_gb, 3) if vram_used_mb is not None else "N/A",
                "queue_size": current_queue_size,
            },
            "budget": {
                "max_ram_gb": self.budget.max_ram_gb,
                "max_gpu_memory_gb": self.budget.max_gpu_memory_gb,
                "max_cpu_percent": self.budget.max_cpu_percent,
                "max_queue_size": self.budget.max_queue_size,
            },
            "remediation": self.get_degraded_remediation() if self._is_degraded else "NONE",
        }

    def get_degraded_remediation(self) -> Dict[str, Any]:
        """Return non-intrusive runtime throttles to shed compute load."""
        return {
            "pose_cadence_override": 3,  # Run pose every 3 frames instead of 1
            "hand_cadence_override": 2,  # Run hands every 2 frames
            "stream_quality_override": "LOW",  # Lower video stream resolution
            "critical_assurance_protected": True,  # Invariant: NEVER disable procedure assurance!
        }

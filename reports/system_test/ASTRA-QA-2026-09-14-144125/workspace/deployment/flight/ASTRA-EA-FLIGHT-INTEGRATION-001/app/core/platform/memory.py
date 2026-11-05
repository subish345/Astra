"""Memory Hardware Abstraction and Allocation Guards for ASTRA-EA (Phase 18)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import psutil


@dataclass
class MemoryCapabilities:
    total_ram_mb: float
    available_ram_mb: float
    used_ram_mb: float
    process_rss_mb: float
    swap_total_mb: float
    swap_used_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ram_mb": self.total_ram_mb,
            "available_ram_mb": self.available_ram_mb,
            "used_ram_mb": self.used_ram_mb,
            "process_rss_mb": self.process_rss_mb,
            "swap_total_mb": self.swap_total_mb,
            "swap_used_mb": self.swap_used_mb,
        }


class MemoryMonitor:
    """Monitors system RAM and enforces process allocation ceilings."""

    def __init__(self, max_rss_mb: float = 1024.0) -> None:
        self.max_rss_mb = max_rss_mb
        self._proc = psutil.Process()
        self._initial_rss = self.get_process_rss_mb()

    def get_capabilities(self) -> MemoryCapabilities:
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return MemoryCapabilities(
            total_ram_mb=round(vm.total / (1024.0 * 1024.0), 1),
            available_ram_mb=round(vm.available / (1024.0 * 1024.0), 1),
            used_ram_mb=round(vm.used / (1024.0 * 1024.0), 1),
            process_rss_mb=self.get_process_rss_mb(),
            swap_total_mb=round(sw.total / (1024.0 * 1024.0), 1),
            swap_used_mb=round(sw.used / (1024.0 * 1024.0), 1),
        )

    def get_process_rss_mb(self) -> float:
        """Process Resident Set Size in megabytes."""
        return round(self._proc.memory_info().rss / (1024.0 * 1024.0), 2)

    def get_drift_percent(self) -> float:
        """Memory drift since monitor initialization."""
        cur = self.get_process_rss_mb()
        if self._initial_rss <= 0:
            return 0.0
        return round(((cur - self._initial_rss) / self._initial_rss) * 100.0, 2)

    def is_within_limits(self) -> bool:
        """Check if process memory is below the flight ceiling."""
        return self.get_process_rss_mb() <= self.max_rss_mb

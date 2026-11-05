"""CPU Hardware Abstraction and Telemetry for ASTRA-EA (Phase 18)."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Any, Dict, Optional

import psutil


@dataclass
class CPUCapabilities:
    architecture: str
    physical_cores: int
    logical_cores: int
    frequency_mhz: Optional[float]
    model_name: str
    throttling_detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "architecture": self.architecture,
            "physical_cores": self.physical_cores,
            "logical_cores": self.logical_cores,
            "frequency_mhz": self.frequency_mhz,
            "model_name": self.model_name,
            "throttling_detected": self.throttling_detected,
        }


class CPUMonitor:
    """Monitors CPU metrics and detects thermal throttling."""

    def __init__(self) -> None:
        self.arch = platform.machine()
        self.physical_cores = psutil.cpu_count(logical=False) or 1
        self.logical_cores = psutil.cpu_count(logical=True) or 1

    def get_capabilities(self) -> CPUCapabilities:
        freq = None
        try:
            f = psutil.cpu_freq()
            if f:
                freq = f.current
        except Exception:
            pass

        model = platform.processor() or "Unknown CPU"
        # On Linux, inspect /proc/cpuinfo if available
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo", "r", encoding="utf-8") as cpuf:
                    for line in cpuf:
                        if "model name" in line:
                            model = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        return CPUCapabilities(
            architecture=self.arch,
            physical_cores=self.physical_cores,
            logical_cores=self.logical_cores,
            frequency_mhz=freq,
            model_name=model,
            throttling_detected=self.check_throttling(),
        )

    def get_utilization_percent(self) -> float:
        """Instantaneous CPU utilization percentage."""
        return psutil.cpu_percent(interval=None)

    def check_throttling(self) -> bool:
        """Check for active CPU thermal throttling (Section 4).

        Evaluates active thermal zones to determine if silicon temperature is currently
        exceeding the critical operating threshold (> 85°C).
        """
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if any(k in name.lower() for k in ("core", "cpu", "k10", "soc", "zen")):
                        for entry in entries:
                            crit = entry.critical or 100.0
                            if entry.current and entry.current >= crit:
                                return True
                return False
        except Exception:
            pass

        # Fallback to sysfs thermal zones only if psutil yielded no temperature sensors
        if os.path.exists("/sys/class/thermal"):
            try:
                for tz in os.listdir("/sys/class/thermal"):
                    if tz.startswith("thermal_zone"):
                        tf = os.path.join("/sys/class/thermal", tz, "temp")
                        type_f = os.path.join("/sys/class/thermal", tz, "type")
                        if os.path.exists(tf):
                            ztype = ""
                            if os.path.exists(type_f):
                                with open(type_f, "r", encoding="utf-8") as yf:
                                    ztype = yf.read().strip().lower()
                            if any(k in ztype for k in ("cpu", "pkg", "core", "x86")):
                                with open(tf, "r", encoding="utf-8") as f:
                                    val = float(f.read().strip()) / 1000.0
                                    if val >= 100.0:
                                        return True
            except Exception:
                pass

        return False

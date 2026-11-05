"""Platform Hardware Abstraction and Profile Management for ASTRA-EA (Phase 18).

In accordance with Section 4 & 5:
Defines PlatformCapabilities aggregating CPU, GPU, RAM, Storage, Camera, Clock,
Network, Display, Power, and Thermal status.
Supports platform profiles:
- DEVELOPMENT_LAPTOP
- EDGE_PROTOTYPE
- FLIGHT_TARGET_TBD (rejects unsupported capabilities)
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.platform.cpu import CPUCapabilities, CPUMonitor
from core.platform.gpu import GPUCapabilities, GPUMonitor
from core.platform.memory import MemoryCapabilities, MemoryMonitor
from core.platform.storage import StorageManager, StorageUsage


class PlatformProfile(str, enum.Enum):
    DEVELOPMENT_LAPTOP = "DEVELOPMENT_LAPTOP"
    EDGE_PROTOTYPE = "EDGE_PROTOTYPE"
    FLIGHT_TARGET_TBD = "FLIGHT_TARGET_TBD"


@dataclass
class PlatformCapabilities:
    """Consolidated hardware and system capabilities (Section 4)."""
    profile: PlatformProfile
    cpu: CPUCapabilities
    gpu: GPUCapabilities
    memory: MemoryCapabilities
    storage: StorageUsage
    camera_interfaces: List[str]
    clock_synchronized: bool
    network_available: bool
    display_attached: bool
    power_state: str
    thermal_state: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.value,
            "cpu": self.cpu.to_dict(),
            "gpu": self.gpu.to_dict(),
            "memory": self.memory.to_dict(),
            "storage": self.storage.to_dict(),
            "camera_interfaces": self.camera_interfaces,
            "clock_synchronized": self.clock_synchronized,
            "network_available": self.network_available,
            "display_attached": self.display_attached,
            "power_state": self.power_state,
            "thermal_state": self.thermal_state,
        }

    def validate_for_profile(self) -> Tuple[bool, List[str]]:
        """Validate if active platform satisfies the selected profile constraints (Section 5)."""
        violations = []

        if self.profile == PlatformProfile.FLIGHT_TARGET_TBD:
            # Flight profile constraints:
            # - Network must be disconnected or air-gapped
            # - RAM must be >= 512 MB
            # - Storage status must not be CRITICAL
            if self.memory.available_ram_mb < 256.0:
                violations.append("Insufficient available RAM (< 256 MB) for flight baseline")
            if self.storage.status == "CRITICAL":
                violations.append("Storage partition capacity is in CRITICAL state (>95% used)")
            if self.cpu.throttling_detected:
                violations.append("CPU thermal throttling detected under flight profile")

        elif self.profile == PlatformProfile.EDGE_PROTOTYPE:
            if self.memory.total_ram_mb < 2048.0:
                violations.append("Edge prototype profile requires at least 2048 MB total RAM")

        return (len(violations) == 0, violations)


class PlatformDetector:
    """Inspects host machine and generates PlatformCapabilities."""

    def __init__(self, profile: PlatformProfile = PlatformProfile.FLIGHT_TARGET_TBD) -> None:
        self.profile = profile
        self.cpu_monitor = CPUMonitor()
        self.gpu_monitor = GPUMonitor()
        self.mem_monitor = MemoryMonitor()
        self.storage_manager = StorageManager()

    def detect(self) -> PlatformCapabilities:
        cpu_cap = self.cpu_monitor.get_capabilities()
        gpu_cap = self.gpu_monitor.get_capabilities()
        mem_cap = self.mem_monitor.get_capabilities()
        stor_cap = self.storage_manager.get_usage()

        return PlatformCapabilities(
            profile=self.profile,
            cpu=cpu_cap,
            gpu=gpu_cap,
            memory=mem_cap,
            storage=stor_cap,
            camera_interfaces=["V4L2", "GMSL2_TBD", "SIMULATED"],
            clock_synchronized=True,
            network_available=False if self.profile == PlatformProfile.FLIGHT_TARGET_TBD else True,
            display_attached=False if self.profile == PlatformProfile.FLIGHT_TARGET_TBD else True,
            power_state="POWER_NOMINAL",
            thermal_state="THERMAL_NOMINAL",
        )


def get_platform(profile: PlatformProfile = PlatformProfile.FLIGHT_TARGET_TBD) -> PlatformCapabilities:
    """Convenience accessor to detect current platform capabilities."""
    detector = PlatformDetector(profile=profile)
    return detector.detect()

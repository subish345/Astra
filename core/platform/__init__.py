"""ASTRA-EA Platform Abstraction Layer (Phase 18).

Provides target hardware decoupling, platform capability detection,
camera and mission clock drivers, storage priority management, and central watchdog.
"""

from core.platform.platform import PlatformCapabilities, PlatformProfile, get_platform
from core.platform.camera import CameraDriver, CameraHealth, CameraState
from core.platform.clock import MissionClock, ClockSource
from core.platform.storage import StorageManager, StoragePriority
from core.platform.watchdog import Watchdog, WatchdogPolicy
from core.platform.health import PlatformHealthMonitor, SubsystemHealth, HealthState

__all__ = [
    "PlatformCapabilities",
    "PlatformProfile",
    "get_platform",
    "CameraDriver",
    "CameraHealth",
    "CameraState",
    "MissionClock",
    "ClockSource",
    "StorageManager",
    "StoragePriority",
    "Watchdog",
    "WatchdogPolicy",
    "PlatformHealthMonitor",
    "SubsystemHealth",
    "HealthState",
]

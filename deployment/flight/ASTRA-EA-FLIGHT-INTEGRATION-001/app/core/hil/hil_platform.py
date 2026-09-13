"""Hardware-in-the-Loop (HIL) Platform Contract for ASTRA-EA (Phase 18).

In accordance with Section 40 & 41:
Provides abstract swap between physical and simulated hardware drivers:
- Real vs Simulated Camera
- Real vs Simulated Clock
- Real vs In-Memory Telemetry
- Real vs Simulated Command Ingestion
Enables identical flight assurance logic to execute in HIL testbeds without code modifications.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from core.platform.camera import CameraDriver, SimulatedCameraDriver
from core.platform.clock import ClockSource, MissionClock
from core.platform.health import PlatformHealthMonitor
from core.platform.storage import StorageManager
from core.platform.watchdog import Watchdog
from integration.commands.interface import CommandDispatcher
from integration.telemetry.publisher import MemoryTelemetryPublisher, TelemetryPublisher

logger = logging.getLogger("hil_platform")


@dataclass
class HILPlatformConfig:
    simulated_camera: bool = True
    simulated_clock: bool = True
    in_memory_telemetry: bool = True
    camera_width: int = 1280
    camera_height: int = 720
    camera_fps: float = 30.0


class HILPlatform:
    """Hardware-in-the-Loop Platform Contract (D18.19)."""

    def __init__(self, config: Optional[HILPlatformConfig] = None) -> None:
        self.config = config or HILPlatformConfig()

        # 1. Clock abstraction
        clock_source = ClockSource.MISSION_CLOCK if self.config.simulated_clock else ClockSource.SYSTEM_CLOCK
        self.clock = MissionClock(clock_source=clock_source)

        # 2. Camera abstraction
        if self.config.simulated_camera:
            self.camera: CameraDriver = SimulatedCameraDriver(
                clock=self.clock,
                width=self.config.camera_width,
                height=self.config.camera_height,
                fps_target=self.config.camera_fps,
            )
        else:
            from core.platform.camera import RealV4L2CameraDriver
            self.camera = RealV4L2CameraDriver(device_id=0, clock=self.clock)

        # 3. Storage abstraction
        self.storage = StorageManager()

        # 4. Telemetry abstraction
        if self.config.in_memory_telemetry:
            self.telemetry: TelemetryPublisher = MemoryTelemetryPublisher()
        else:
            from integration.telemetry.publisher import FileTelemetryPublisher
            self.telemetry = FileTelemetryPublisher()

        # 5. Command dispatcher
        self.commands = CommandDispatcher()

        # 6. Watchdog and health monitor
        self.watchdog = Watchdog()
        self.health = PlatformHealthMonitor()

    def initialize(self) -> bool:
        """Initialize all HIL platform subsystems."""
        self.clock.start_mission()
        cam_ok = self.camera.initialize() and self.camera.start()
        self.watchdog.feed("camera")
        self.watchdog.feed("main_process")
        return cam_ok

    def inject_camera_fault(self, fail: bool = True) -> None:
        """Inject camera failure in HIL testbed."""
        if isinstance(self.camera, SimulatedCameraDriver):
            self.camera.inject_failure(fail)

    def inject_telemetry_disconnect(self, disconnect: bool = True) -> None:
        """Inject ground telemetry link drop."""
        self.telemetry.is_connected = not disconnect

    def shutdown(self) -> None:
        """Orderly safe shutdown of HIL platform."""
        self.camera.stop()

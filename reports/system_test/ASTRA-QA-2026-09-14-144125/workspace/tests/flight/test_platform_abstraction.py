"""Automated Test Suite for Platform Abstraction Layer (Phase 18)."""

import pytest

from core.platform.camera import CameraHealth, CameraState, SimulatedCameraDriver
from core.platform.clock import ClockSource, MissionClock
from core.platform.cpu import CPUMonitor
from core.platform.gpu import GPUMonitor
from core.platform.health import HealthState, PlatformHealthMonitor
from core.platform.memory import MemoryMonitor
from core.platform.platform import PlatformCapabilities, PlatformProfile, get_platform
from core.platform.storage import StorageManager, StoragePriority
from core.platform.watchdog import Watchdog, WatchdogPolicy


def test_platform_capabilities_detection():
    """Verify platform capabilities detection across profiles."""
    cap = get_platform(profile=PlatformProfile.FLIGHT_TARGET_TBD)
    assert cap.profile == PlatformProfile.FLIGHT_TARGET_TBD
    assert cap.cpu.logical_cores >= 1
    assert cap.memory.total_ram_mb > 0
    assert cap.storage.total_capacity_mb > 0
    assert "V4L2" in cap.camera_interfaces

    # Validation against flight profile
    is_valid, violations = cap.validate_for_profile()
    assert is_valid is True, f"Violations: {violations}"

    # Verify serialization
    d = cap.to_dict()
    assert d["profile"] == "FLIGHT_TARGET_TBD"
    assert "cpu" in d
    assert "memory" in d


def test_cpu_and_gpu_monitors():
    """Verify CPU and GPU capability monitors."""
    cpu_m = CPUMonitor()
    cpu_caps = cpu_m.get_capabilities()
    assert cpu_caps.physical_cores >= 1
    assert cpu_m.get_utilization_percent() >= 0.0

    gpu_m = GPUMonitor()
    gpu_caps = gpu_m.get_capabilities()
    assert gpu_caps.accelerator_type in ("CUDA", "TENSORRT", "NPU", "NONE")


def test_memory_monitor_and_limits():
    """Verify memory monitor, RSS calculation, and headroom limits."""
    mem_m = MemoryMonitor(max_rss_mb=10000.0)
    caps = mem_m.get_capabilities()
    assert caps.total_ram_mb > 0
    assert caps.process_rss_mb > 0
    assert mem_m.is_within_limits() is True
    assert isinstance(mem_m.get_drift_percent(), float)


def test_mission_clock():
    """Verify MissionClock timestamps, monotonic time, and MET."""
    clock = MissionClock(clock_source=ClockSource.SYSTEM_CLOCK)
    assert clock.get_met_seconds() == 0.0

    clock.start_mission()
    assert clock.get_met_seconds() >= 0.0

    frame_ts = clock.stamp_frame(frame_index=1)
    assert frame_ts.frame_index == 1
    assert "T" in frame_ts.utc_iso and "Z" in frame_ts.utc_iso

    event_ts_1 = clock.stamp_event()
    event_ts_2 = clock.stamp_event()
    assert event_ts_2.sequence_number == event_ts_1.sequence_number + 1

    status = clock.get_status()
    assert status["sequence_count"] >= 2


def test_camera_driver_and_failure_degradation():
    """Verify CameraDriver, frame acquisition, and failure transition (Section 15)."""
    clock = MissionClock()
    camera = SimulatedCameraDriver(clock=clock, width=640, height=480)

    assert camera.state == CameraState.UNINITIALIZED
    assert camera.initialize() is True
    assert camera.start() is True
    assert camera.state == CameraState.STREAMING

    # Read frame
    ret = camera.read_frame()
    assert ret is not None
    frame, ts = ret
    assert frame.shape == (480, 640, 3)
    assert ts.frame_index == 1

    health = camera.health()
    assert health.state == CameraState.STREAMING
    assert health.frame_count == 1

    # Inject failure -> consecutive drops -> CAMERA_FAILED
    camera.inject_failure(True)
    drop_ret = camera.read_frame()
    assert drop_ret is None
    assert camera.state == CameraState.FAILED
    assert camera.health().consecutive_drop_count >= 5

    camera.stop()
    assert camera.state == CameraState.STOPPED


def test_storage_manager_and_priority_pruning(tmp_path):
    """Verify storage partitions and priority pruning rules (Section 28)."""
    stor = StorageManager(base_dir=tmp_path / "flight_data")
    assert stor.mission_dir.exists()
    assert stor.evidence_dir.exists()
    assert stor.telemetry_dir.exists()
    assert stor.diagnostics_dir.exists()

    # Create dummy diagnostic file and mission event file
    diag_file = stor.diagnostics_dir / "debug.log"
    diag_file.write_text("debug trace", encoding="utf-8")
    mission_file = stor.mission_dir / "mission_event.json"
    mission_file.write_text("{\"event\": 1}", encoding="utf-8")

    usage = stor.get_usage()
    assert usage.status in ("NOMINAL", "WARNING", "CRITICAL")

    # Prune lowest priority: diagnostics must be removed, mission event preserved!
    pruned = stor.prune_lowest_priority()
    assert str(diag_file) in pruned
    assert not diag_file.exists()
    assert mission_file.exists(), "Mission-critical events must NEVER be pruned"


def test_watchdog_monitoring_and_action():
    """Verify central watchdog heartbeats and timeout action (Section 12 & 13)."""
    wd = Watchdog(default_policy=WatchdogPolicy.ENTER_DEGRADED, default_timeout_seconds=0.1)
    wd.register("camera", timeout_seconds=0.1)
    wd.feed("camera")

    # Immediately checking should show healthy
    check_1 = wd.check()
    assert check_1["all_healthy"] is True

    # Sleep beyond timeout
    import time
    time.sleep(0.15)
    check_2 = wd.check()
    assert check_2["all_healthy"] is False
    assert "camera" in check_2["unhealthy_subsystems"]
    assert check_2["triggered_actions"][0]["action"] == "ENTER_DEGRADED"


def test_platform_health_monitor():
    """Verify health aggregator combines subsystems into READY, DEGRADED, FAILED."""
    hm = PlatformHealthMonitor()
    assert hm.evaluate_overall_health() == HealthState.READY

    # Degrade camera
    hm.update_subsystem("CAMERA", HealthState.DEGRADED, "Frame rate dropped")
    assert hm.evaluate_overall_health() == HealthState.DEGRADED

    # Fail model
    hm.update_subsystem("MODEL", HealthState.FAILED, "OOM crash")
    assert hm.evaluate_overall_health() == HealthState.FAILED

    rep = hm.to_report()
    assert rep["overall_status"] == "FAILED"
    assert rep["subsystems"]["CAMERA"]["state"] == "DEGRADED"
    assert rep["subsystems"]["MODEL"]["state"] == "FAILED"

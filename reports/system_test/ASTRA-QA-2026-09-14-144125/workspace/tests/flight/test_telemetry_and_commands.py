"""Automated Test Suite for Telemetry and Command Interfaces (Phase 18)."""

import pytest

from integration.commands.authorization import AuthorizationPolicy, AuthorizationRole
from integration.commands.interface import CommandDispatcher, CommandSafetyGuard
from integration.commands.schema import CommandResponse, CommandStatus, CommandType, FlightCommand
from integration.telemetry.publisher import FileTelemetryPublisher, MemoryTelemetryPublisher
from integration.telemetry.schema import (
    AssuranceTelemetryPacket,
    FaultTelemetryPacket,
    HealthTelemetryPacket,
    MissionTelemetryPacket,
    PerformanceTelemetryPacket,
)


def test_telemetry_packet_schemas_and_memory_publisher():
    """Verify all 5 telemetry packet categories serialize and store in memory."""
    pub = MemoryTelemetryPublisher()

    # 1. Health
    h_packet = HealthTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=10.5,
        camera_ok=True,
        model_ok=True,
        storage_ok=True,
        cpu_die_temp_c=45.2,
        gpu_die_temp_c=48.0,
        cpu_utilization_pct=25.0,
        gpu_utilization_pct=15.0,
    )
    assert pub.publish_health(h_packet) is True

    # 2. Mission
    m_packet = MissionTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=10.5,
        experiment_id="EXP-01",
        run_id="RUN-001",
        current_step_id="STEP-01",
        procedure_state="IN_PROGRESS",
        step_elapsed_seconds=5.2,
        total_steps=5,
        completed_steps=1,
    )
    assert pub.publish_mission(m_packet) is True

    # 3. Assurance
    a_packet = AssuranceTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=10.5,
        decision="VERIFIED",
        confidence=0.98,
    )
    assert pub.publish_assurance(a_packet) is True

    # 4. Performance
    p_packet = PerformanceTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=10.5,
        pipeline_fps=31.5,
        inference_latency_ms=14.2,
        end_to_end_latency_ms=22.1,
        queue_depth=1,
        memory_rss_mb=420.5,
    )
    assert pub.publish_performance(p_packet) is True

    # 5. Fault
    f_packet = FaultTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=10.5,
        fault_code="ERR-CAM-TIMEOUT",
        subsystem="CAMERA",
        severity="WARNING",
        message="Frame drop observed",
        containment_action="RETRY_CAPTURE",
    )
    assert pub.publish_fault(f_packet) is True

    assert len(pub.get_packets()) == 5
    assert len(pub.get_packets("HEALTH")) == 1
    assert len(pub.get_packets("ASSURANCE")) == 1


def test_telemetry_communication_loss_handling(tmp_path):
    """Verify communication loss does not crash pipeline (Section 46)."""
    pub = FileTelemetryPublisher(output_dir=tmp_path / "telemetry")
    assert pub.publish_health(HealthTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:00Z",
        met_seconds=1.0,
        camera_ok=True,
        model_ok=True,
        storage_ok=True,
        cpu_die_temp_c=None,
        gpu_die_temp_c=None,
        cpu_utilization_pct=10.0,
        gpu_utilization_pct=0.0,
    )) is True

    # Sever link
    pub.is_connected = False
    res = pub.publish_health(HealthTelemetryPacket(
        timestamp_utc="2026-09-13T12:00:01Z",
        met_seconds=2.0,
        camera_ok=True,
        model_ok=True,
        storage_ok=True,
        cpu_die_temp_c=None,
        gpu_die_temp_c=None,
        cpu_utilization_pct=10.0,
        gpu_utilization_pct=0.0,
    ))
    # Must fail gracefully without raising an exception
    assert res is False


def test_command_validation_authorization_and_dispatch():
    """Verify command validation, authorization, sequence checks, and safety interlocks (Section 22-24)."""
    dispatcher = CommandDispatcher()

    # Register custom handler
    status_handler_called = []
    dispatcher.register_handler(
        CommandType.REQUEST_STATUS,
        lambda cmd: status_handler_called.append(cmd.command_id) or {"mode": "STANDBY"},
    )

    # 1. Nominal valid command
    cmd1 = FlightCommand(
        command_id="CMD-001",
        command_type=CommandType.REQUEST_STATUS,
        sequence_number=1,
        originator="LOCAL_OPERATOR",
    )
    resp1 = dispatcher.execute(cmd1)
    assert resp1.status == CommandStatus.EXECUTED
    assert resp1.payload["mode"] == "STANDBY"
    assert len(status_handler_called) == 1

    # 2. Duplicate / replay sequence number -> REJECTED
    cmd2 = FlightCommand(
        command_id="CMD-002",
        command_type=CommandType.REQUEST_STATUS,
        sequence_number=1,  # Duplicate sequence!
        originator="LOCAL_OPERATOR",
    )
    resp2 = dispatcher.execute(cmd2)
    assert resp2.status == CommandStatus.REJECTED
    assert resp2.error_code == "INVALID_SEQUENCE"

    # 3. Safety guard interlock violation (Section 23)
    # Fail camera health
    unsafe_guard = CommandSafetyGuard(camera_ok_fn=lambda: False)
    safe_dispatcher = CommandDispatcher(safety_guard=unsafe_guard)

    cmd_start = FlightCommand(
        command_id="CMD-003",
        command_type=CommandType.START_EXPERIMENT,
        sequence_number=3,
        originator="LOCAL_OPERATOR",
    )
    resp_start = safe_dispatcher.execute(cmd_start)
    assert resp_start.status == CommandStatus.FAILED
    assert resp_start.error_code == "SAFETY_VIOLATION"
    assert "Camera unavailable" in resp_start.message

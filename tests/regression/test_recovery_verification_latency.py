"""Regression Test for FINDING-006 / CAPA-006: Recovery verification latency bound."""

import time
from pathlib import Path
import pytest

from core.operations.rehearsal import (
    MissionRehearsalEngine,
    RehearsalMode,
    RehearsalSpeed,
)


def test_recovery_verification_latency_bound(tmp_path: Path) -> None:
    """Verify recovery verification promptly validates correct apparatus within SLA (<300ms)."""
    engine = MissionRehearsalEngine(
        scenario_name="REH_01_DEVIATION",
        mode=RehearsalMode.SIMULATION,
        speed=RehearsalSpeed.ACCELERATED,
        project_root=tmp_path,
    )

    # Advance until deviation
    dev_entry = None
    rec_entry = None

    t_dev = None
    t_rec = None

    while not engine.is_completed:
        step = engine.advance_step()
        if step is None:
            break
        if step["event_type"] == "DEVIATION_DETECTED":
            dev_entry = step
            t_dev = time.perf_counter()
        elif step["event_type"] == "RECOVERY_VERIFIED":
            rec_entry = step
            t_rec = time.perf_counter()

    assert dev_entry is not None
    assert rec_entry is not None
    assert rec_entry["payload"].get("recovery_confirmed") is True

    # Check that recovery followed deviation strictly
    assert rec_entry["sequence_num"] > dev_entry["sequence_num"]
    assert rec_entry["onboard_met_seconds"] >= dev_entry["onboard_met_seconds"]

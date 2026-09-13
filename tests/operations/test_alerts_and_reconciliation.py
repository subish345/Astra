"""Automated Tests for Alert System, Prioritization, and Sequence Reconciliation (Phase 19, D19.08, D19.20)."""

import pytest

from core.operations.alerts import (
    AlertLifecycle,
    AlertManager,
    AlertSeverity,
    EscalationLevel,
)
from core.operations.reconciliation import GroundReconciler


def test_alert_lifecycle_and_prioritization():
    """Verify alert progression and strict severity hierarchy (CRITICAL > WARNING > NOTICE > INFO)."""
    mgr = AlertManager()

    # Post alerts of varying severities
    a_info = mgr.post_alert("ALT_01", AlertSeverity.INFO, "TELEMETRY", "Nominal ping")
    a_warn = mgr.post_alert("ALT_02", AlertSeverity.WARNING, "ASSURANCE", "Wrong apparatus interaction")
    a_crit = mgr.post_alert("ALT_03", AlertSeverity.CRITICAL, "CAMERA", "Optical stream lost")

    # Dominant alert should be CRITICAL
    dominant = mgr.get_dominant_alert()
    assert dominant is not None
    assert dominant.alert_id == "ALT_03"
    assert dominant.severity == AlertSeverity.CRITICAL
    assert dominant.lifecycle_state == AlertLifecycle.RECEIVED

    # Acknowledge critical alert (Section 17: ACKNOWLEDGED does not mean RESOLVED)
    mgr.acknowledge_alert("ALT_03", operator="Astronaut_01")
    assert dominant.lifecycle_state == AlertLifecycle.ACKNOWLEDGED
    assert dominant.acknowledged_by == "Astronaut_01"

    # Resolving critical alert promotes next highest unresolved (WARNING)
    mgr.resolve_alert("ALT_03", operator="Astronaut_01", notes="Camera re-connected")
    assert dominant.lifecycle_state == AlertLifecycle.RESOLVED

    dominant_next = mgr.get_dominant_alert()
    assert dominant_next is not None
    assert dominant_next.alert_id == "ALT_02"
    assert dominant_next.severity == AlertSeverity.WARNING


def test_ground_reconciler_gap_detection_and_recovery():
    """Verify sequence gap detection and reconciliation without duplicating events (Section 43, 44)."""
    reconciler = GroundReconciler()
    reconciler.mark_connection_status(True)

    # Ingest event 1, 2, 3
    for seq in [1, 2, 3]:
        is_new, gap = reconciler.ingest_event({"sequence_num": seq, "name": f"Event {seq}"})
        assert is_new is True
        assert gap is None

    # Connection drops, misses 4, 5, receives 6
    reconciler.mark_connection_status(False)
    reconciler.mark_connection_status(True)
    is_new, gap = reconciler.ingest_event({"sequence_num": 6, "name": "Event 6"})
    assert is_new is True
    assert gap == (4, 5)  # Gap correctly identified

    # Reconcile with backlog
    missed_batch = [
        {"sequence_num": 4, "name": "Event 4"},
        {"sequence_num": 5, "name": "Event 5"},
        {"sequence_num": 2, "name": "Event 2 Duplicate"},  # Duplicate to test discard
    ]
    rep = reconciler.reconcile_buffered_events(missed_batch)
    assert rep.recovered_events_count == 2
    assert rep.duplicate_events_discarded == 1
    assert len(rep.detected_gaps) == 0

    # Ensure final event log is sorted and contiguous
    seqs = [e["sequence_num"] for e in reconciler.ordered_event_log]
    assert seqs == [1, 2, 3, 4, 5, 6]

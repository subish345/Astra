"""Regression Test for FINDING-002 / CAPA-002: Ground reconnect sequence gap deduplication."""

import pytest

from core.operations.reconciliation import GroundReconciler


def test_reconciliation_zero_duplicates() -> None:
    """Verify that reconnecting after mid-burst LOS suppresses duplicate sequence entries."""
    reconciler = GroundReconciler()

    # Initial ground reception: events 100, 101, 102
    for seq in [100, 101, 102]:
        is_new, gap = reconciler.ingest_event({
            "sequence_num": seq,
            "event_type": f"STEP_{seq}",
            "timestamp_utc": f"2026-09-13T12:00:0{seq-100}Z",
        })
        assert is_new is True
        assert gap is None
    assert reconciler.last_seen_sequence == 102

    # Inbound replayed events from onboard after reconnect: seq 102 (overlapping), 103, 104
    replayed_batch = [
        {"sequence_num": 102, "event_type": "STEP_102", "timestamp_utc": "2026-09-13T12:00:02Z"},
        {"sequence_num": 103, "event_type": "STEP_103", "timestamp_utc": "2026-09-13T12:00:03Z"},
        {"sequence_num": 104, "event_type": "STEP_104", "timestamp_utc": "2026-09-13T12:00:04Z"},
    ]

    report = reconciler.reconcile_buffered_events(replayed_batch)
    assert report.recovered_events_count == 2      # 103 and 104
    assert report.duplicate_events_discarded == 1  # 102 discarded

    # Check full local store sequence is strictly monotonic with 0 duplicates
    all_seqs = [e["sequence_num"] for e in reconciler.ordered_event_log]
    assert all_seqs == [100, 101, 102, 103, 104]
    assert len(all_seqs) == len(set(all_seqs))

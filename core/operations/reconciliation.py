"""Ground Telemetry Sequence Gap Detection and State Reconciliation (Phase 19, Section 41-44, D19.20).

Enables Ground Monitor to detect sequence gaps in streaming events, track connection
disconnections, buffer onboard events, and reconcile missed events upon reconnection without duplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ReconciliationReport:
    """Outcome of a sequence reconciliation pass."""
    reconciled_at_utc: str
    last_known_seq: int
    new_highest_seq: int
    detected_gaps: List[Tuple[int, int]]  # List of (start_seq, end_seq) ranges
    recovered_events_count: int
    duplicate_events_discarded: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reconciled_at_utc": self.reconciled_at_utc,
            "last_known_seq": self.last_known_seq,
            "new_highest_seq": self.new_highest_seq,
            "detected_gaps": [list(g) for g in self.detected_gaps],
            "recovered_events_count": self.recovered_events_count,
            "duplicate_events_discarded": self.duplicate_events_discarded,
        }


class GroundReconciler:
    """Manages ground-side sequence tracking, gap detection, and state reconciliation."""

    def __init__(self) -> None:
        self.last_seen_sequence: int = -1
        self.received_sequence_numbers: Set[int] = set()
        self.ordered_event_log: List[Dict[str, Any]] = []
        self.detected_gaps: List[Tuple[int, int]] = []
        self.is_connected: bool = False
        self.disconnect_timestamp_utc: Optional[str] = None
        self.reconnect_timestamp_utc: Optional[str] = None

    def mark_connection_status(self, connected: bool) -> None:
        """Track connection transitions for disconnect/reconnect procedures (Section 42)."""
        now_utc = datetime.now(timezone.utc).isoformat()
        if self.is_connected and not connected:
            self.disconnect_timestamp_utc = now_utc
        elif not self.is_connected and connected:
            self.reconnect_timestamp_utc = now_utc
        self.is_connected = connected

    def ingest_event(self, event: Dict[str, Any]) -> Tuple[bool, Optional[Tuple[int, int]]]:
        """Ingest incoming telemetry event, check for monotonic sequence and detect gaps.

        Returns:
            (is_new_event, detected_gap_range_or_none)
        """
        seq = event.get("sequence_num")
        if seq is None:
            return False, None

        # Check for duplication (Section 43: Do not duplicate events)
        if seq in self.received_sequence_numbers:
            return False, None

        gap_detected = None
        if self.last_seen_sequence >= 0 and seq > self.last_seen_sequence + 1:
            # Sequence jump! We missed (self.last_seen_sequence + 1, seq - 1)
            gap = (self.last_seen_sequence + 1, seq - 1)
            self.detected_gaps.append(gap)
            gap_detected = gap

        self.received_sequence_numbers.add(seq)
        self.ordered_event_log.append(event)
        if seq > self.last_seen_sequence:
            self.last_seen_sequence = seq

        return True, gap_detected

    def reconcile_buffered_events(self, missed_events: List[Dict[str, Any]]) -> ReconciliationReport:
        """Incorporate missed events retrieved from onboard buffer upon reconnect (Section 43)."""
        old_seq = self.last_seen_sequence
        recovered = 0
        duplicates = 0

        for evt in missed_events:
            seq = evt.get("sequence_num")
            if seq is not None:
                if seq in self.received_sequence_numbers:
                    duplicates += 1
                else:
                    self.received_sequence_numbers.add(seq)
                    self.ordered_event_log.append(evt)
                    recovered += 1
                    if seq > self.last_seen_sequence:
                        self.last_seen_sequence = seq

        # Sort combined event log by sequence number
        self.ordered_event_log.sort(key=lambda e: e.get("sequence_num", 0))

        # Re-evaluate remaining gaps
        remaining_gaps = []
        if self.ordered_event_log:
            first_seq = self.ordered_event_log[0].get("sequence_num", 0)
            curr = first_seq
            for e in self.ordered_event_log[1:]:
                next_seq = e.get("sequence_num", curr)
                if next_seq > curr + 1:
                    remaining_gaps.append((curr + 1, next_seq - 1))
                curr = next_seq
        self.detected_gaps = remaining_gaps

        return ReconciliationReport(
            reconciled_at_utc=datetime.now(timezone.utc).isoformat(),
            last_known_seq=old_seq,
            new_highest_seq=self.last_seen_sequence,
            detected_gaps=self.detected_gaps,
            recovered_events_count=recovered,
            duplicate_events_discarded=duplicates,
        )

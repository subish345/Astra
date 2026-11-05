"""Mission Timeline Model and Authoritative Timestamps for ASTRA-EA (Phase 19, Section 12, 13, D19.02).

Maintains mission event timelines, anchoring all milestones to authoritative onboard
Mission Elapsed Time (MET) while mapping Ground Receipt Time (GRT).
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TimelineMilestone:
    """A milestone entry on the operational timeline."""
    sequence_num: int
    milestone_type: str  # T_START | INITIALIZATION | EXPERIMENT_START | STEP_TRANSITION | DEVIATION | RECOVERY | COMPLETION | POST_MISSION
    title: str
    details: str
    onboard_met_seconds: float
    onboard_timestamp_utc: str
    ground_receipt_timestamp_utc: Optional[str] = None
    severity: str = "INFO"
    related_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MissionTimeline:
    """Maintains sequential mission timeline entries and provides dual clock mappings."""

    def __init__(self, mission_id: str = "DEMO_EXP_001", run_id: str = "RUN_0001") -> None:
        self.mission_id = mission_id
        self.run_id = run_id
        self.t_start_monotonic: Optional[float] = None
        self.t_start_utc: Optional[str] = None
        self.milestones: List[TimelineMilestone] = []
        self._sequence_counter: int = 0

    def start_timeline(self) -> None:
        """Mark T-START of the mission."""
        self.t_start_monotonic = time.monotonic()
        self.t_start_utc = datetime.now(timezone.utc).isoformat()
        self.record_milestone(
            milestone_type="T_START",
            title="Mission Clock Initiated (T-0)",
            details="Authoritative onboard monotonic reference started.",
            severity="INFO",
        )

    def get_current_met(self) -> float:
        """Calculate current Mission Elapsed Time in seconds (Section 13)."""
        if self.t_start_monotonic is None:
            return 0.0
        return max(0.0, time.monotonic() - self.t_start_monotonic)

    def record_milestone(
        self,
        milestone_type: str,
        title: str,
        details: str = "",
        severity: str = "INFO",
        related_id: Optional[str] = None,
        ground_receipt_time_utc: Optional[str] = None,
    ) -> TimelineMilestone:
        """Append an authoritative milestone to the mission timeline."""
        self._sequence_counter += 1
        now_utc = datetime.now(timezone.utc).isoformat()
        grt = ground_receipt_time_utc or now_utc

        ms = TimelineMilestone(
            sequence_num=self._sequence_counter,
            milestone_type=milestone_type,
            title=title,
            details=details,
            onboard_met_seconds=round(self.get_current_met(), 3),
            onboard_timestamp_utc=now_utc,
            ground_receipt_timestamp_utc=grt,
            severity=severity,
            related_id=related_id,
        )
        self.milestones.append(ms)
        return ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "run_id": self.run_id,
            "t_start_utc": self.t_start_utc,
            "current_met_seconds": round(self.get_current_met(), 3),
            "total_milestones": len(self.milestones),
            "milestones": [m.to_dict() for m in self.milestones],
        }

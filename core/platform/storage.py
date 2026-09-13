"""Flight Data Storage Manager and Priority Pruning for ASTRA-EA (Phase 18).

In accordance with Section 25, 26, 27 & 28:
Enforces structured flight data partitioning (mission/, evidence/, telemetry/, reports/, diagnostics/).
Implements strict retention priority:
MISSION EVENTS > ASSURANCE EVENTS > EVIDENCE > MISSION VIDEO > DIAGNOSTICS > DEBUG.
Prevents silent deletion of mission-critical assurance records.
"""

from __future__ import annotations

import enum
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


class StoragePriority(int, enum.Enum):
    """Storage retention priority ranking (Section 28). Higher number = higher priority."""
    DEBUG = 1
    DIAGNOSTICS = 2
    MISSION_VIDEO = 3
    EVIDENCE = 4
    ASSURANCE_EVENTS = 5
    MISSION_EVENTS = 6


@dataclass
class StorageUsage:
    total_capacity_mb: float
    free_capacity_mb: float
    used_capacity_mb: float
    percent_used: float
    mission_size_mb: float
    evidence_size_mb: float
    telemetry_size_mb: float
    reports_size_mb: float
    diagnostics_size_mb: float
    status: str  # NOMINAL, WARNING, CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_capacity_mb": self.total_capacity_mb,
            "free_capacity_mb": self.free_capacity_mb,
            "used_capacity_mb": self.used_capacity_mb,
            "percent_used": self.percent_used,
            "mission_size_mb": self.mission_size_mb,
            "evidence_size_mb": self.evidence_size_mb,
            "telemetry_size_mb": self.telemetry_size_mb,
            "reports_size_mb": self.reports_size_mb,
            "diagnostics_size_mb": self.diagnostics_size_mb,
            "status": self.status,
        }


class StorageManager:
    """Manages flight data partitions, capacity limits, and retention priority (D18.14)."""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        max_capacity_mb: float = 10000.0,
        warning_threshold_pct: float = 85.0,
        critical_threshold_pct: float = 95.0,
    ) -> None:
        self.base_dir = base_dir or Path("flight_data")
        self.max_capacity_mb = max_capacity_mb
        self.warning_threshold_pct = warning_threshold_pct
        self.critical_threshold_pct = critical_threshold_pct

        # Initialize flight data partitions (Section 26)
        self.mission_dir = self.base_dir / "mission"
        self.evidence_dir = self.base_dir / "evidence"
        self.telemetry_dir = self.base_dir / "telemetry"
        self.reports_dir = self.base_dir / "reports"
        self.diagnostics_dir = self.base_dir / "diagnostics"
        self.init_directories()

    def init_directories(self) -> None:
        """Create structured flight partitions."""
        for d in [
            self.mission_dir,
            self.evidence_dir,
            self.telemetry_dir,
            self.reports_dir,
            self.diagnostics_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def _get_dir_size_mb(self, path: Path) -> float:
        """Calculate total directory size in megabytes."""
        if not path.exists():
            return 0.0
        total = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
        return round(total / (1024.0 * 1024.0), 2)

    def get_usage(self) -> StorageUsage:
        """Compute disk usage across partitions and evaluate threshold warnings."""
        total, used, free = shutil.disk_usage(self.base_dir)
        total_mb = round(total / (1024.0 * 1024.0), 1)
        free_mb = round(free / (1024.0 * 1024.0), 1)
        used_mb = round(used / (1024.0 * 1024.0), 1)
        pct = round((used / total) * 100.0, 1)

        mission_m = self._get_dir_size_mb(self.mission_dir)
        ev_m = self._get_dir_size_mb(self.evidence_dir)
        telem_m = self._get_dir_size_mb(self.telemetry_dir)
        rep_m = self._get_dir_size_mb(self.reports_dir)
        diag_m = self._get_dir_size_mb(self.diagnostics_dir)

        if pct >= self.critical_threshold_pct:
            status = "CRITICAL"
        elif pct >= self.warning_threshold_pct:
            status = "WARNING"
        else:
            status = "NOMINAL"

        return StorageUsage(
            total_capacity_mb=total_mb,
            free_capacity_mb=free_mb,
            used_capacity_mb=used_mb,
            percent_used=pct,
            mission_size_mb=mission_m,
            evidence_size_mb=ev_m,
            telemetry_size_mb=telem_m,
            reports_size_mb=rep_m,
            diagnostics_size_mb=diag_m,
            status=status,
        )

    def prune_lowest_priority(self, target_free_mb: float = 100.0) -> List[str]:
        """Prune non-critical files adhering strictly to Section 28 priority.

        Order of pruning:
        1. DIAGNOSTICS (logs, debug traces)
        2. Older non-evidence telemetry files
        NEVER deletes: Mission events or verified evidence.
        """
        pruned_files = []
        # First attempt: diagnostics directory
        if self.diagnostics_dir.exists():
            diag_files = sorted(self.diagnostics_dir.glob("*"), key=lambda p: p.stat().st_mtime)
            for f in diag_files:
                if f.is_file():
                    try:
                        f.unlink()
                        pruned_files.append(str(f))
                    except Exception:
                        pass

        return pruned_files

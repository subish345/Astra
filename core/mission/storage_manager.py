"""Storage and Directory Management for ASTRA-EA.

Monitors disk capacity, tracks dataset/recording/evidence directory growth,
ensures canonical directory initialization, and warns of storage backpressure.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.common.logging import get_logger

logger = get_logger("STORAGE_MANAGER")

DEFAULT_DIRS = [
    "data/runs",
    "data/recordings",
    "data/evidence/snapshots",
    "data/evidence/clips",
    "data/evidence/metadata",
    "data/reports",
    "data/logs",
    "storage/database",
    "storage/reports",
]


class StorageManager:
    """Manages filesystem layout, directory integrity, and disk capacity monitoring."""

    def __init__(self, root_dir: str = ".", min_free_gb: float = 2.0) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.min_free_gb = min_free_gb
        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Create all standardized directory roots if missing."""
        for d in DEFAULT_DIRS:
            p = self.root_dir / d
            p.mkdir(parents=True, exist_ok=True)

    def get_disk_usage(self) -> Dict[str, Any]:
        """Query partition storage stats where ASTRA is installed."""
        total, used, free = shutil.disk_usage(str(self.root_dir))
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        used_pct = (used / total) * 100.0 if total > 0 else 0.0

        is_low = free_gb < self.min_free_gb
        if is_low:
            logger.warning("Low disk space warning: %.2f GB remaining (< %.2f GB min)", free_gb, self.min_free_gb)

        return {
            "root_path": str(self.root_dir),
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "used_percent": round(used_pct, 1),
            "low_space_warning": is_low,
        }

    def get_directory_sizes(self) -> Dict[str, float]:
        """Compute disk usage in MB across key data stores."""
        sizes_mb: Dict[str, float] = {}
        for d in ["data/runs", "data/recordings", "data/evidence", "storage"]:
            target = self.root_dir / d
            if target.exists():
                total_bytes = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
                sizes_mb[d] = round(total_bytes / (1024 * 1024), 2)
            else:
                sizes_mb[d] = 0.0
        return sizes_mb

    def health_check(self) -> Dict[str, Any]:
        """Storage health assessment for system health aggregator."""
        usage = self.get_disk_usage()
        status = "FAILED" if usage["free_gb"] < 0.5 else "DEGRADED" if usage["low_space_warning"] else "NORMAL"
        return {
            "status": status,
            "free_gb": usage["free_gb"],
            "used_percent": usage["used_percent"],
            "directory_sizes_mb": self.get_directory_sizes(),
        }

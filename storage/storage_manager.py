"""Storage abstraction for ASTRA-EA.

Manages video recordings, evidence clips, audit logs, and reports with path traversal
sanitization and capacity monitoring.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from core.common.config import get_project_root
from core.common.logging import get_logger

logger = get_logger("STORAGE")


class StorageManager:
    """Manages filesystem layout and enforces directory bounds for ASTRA-EA artifacts."""

    def __init__(
        self,
        base_dir: str | Path = "storage",
        max_storage_gb: float = 50.0,
        project_root: Optional[Path] = None,
    ):
        self.root = project_root or get_project_root()
        self.base_dir = self._resolve_safe_path(base_dir)
        self.video_dir = self.base_dir / "video"
        self.evidence_dir = self.base_dir / "evidence"
        self.reports_dir = self.base_dir / "reports"
        self.database_dir = self.base_dir / "database"
        self.max_storage_gb = max_storage_gb

        self.initialize_directories()

    def _resolve_safe_path(self, target: str | Path) -> Path:
        """Resolve path and guard against directory traversal attacks."""
        path = Path(target)
        if not path.is_absolute():
            path = self.root / path
        resolved = path.resolve()
        # Ensure path is within project root or designated base
        if not str(resolved).startswith(str(self.root.resolve())):
            raise ValueError(f"Path traversal detected: {target} resolves outside project root.")
        return resolved

    def initialize_directories(self) -> None:
        """Ensure all required storage folders exist."""
        for d in (self.video_dir, self.evidence_dir, self.reports_dir, self.database_dir):
            d.mkdir(parents=True, exist_ok=True)

    def get_evidence_clip_dir(self, event_id: str) -> Path:
        """Return dedicated directory for an event's evidence clip and metadata."""
        # Sanitize event_id for filename safety
        safe_id = "".join(c for c in event_id if c.isalnum() or c in ("-", "_"))
        target = self.evidence_dir / safe_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def get_report_path(self, filename: str) -> Path:
        """Return path for an audit or mission report."""
        safe_name = Path(filename).name
        return self.reports_dir / safe_name

    def get_video_path(self, filename: str) -> Path:
        """Return path for a video recording segment."""
        safe_name = Path(filename).name
        return self.video_dir / safe_name

    def get_storage_metrics(self) -> Dict[str, Any]:
        """Compute disk usage statistics for the storage directory."""
        total, used, free = shutil.disk_usage(self.base_dir)
        # Calculate size of storage folder specifically
        folder_size = 0
        for dirpath, _, filenames in os.walk(self.base_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    folder_size += os.path.getsize(fp)

        folder_gb = folder_size / (1024 ** 3)
        disk_free_gb = free / (1024 ** 3)

        return {
            "storage_used_gb": round(folder_gb, 3),
            "storage_limit_gb": self.max_storage_gb,
            "disk_free_gb": round(disk_free_gb, 2),
            "usage_percent": round((folder_gb / self.max_storage_gb) * 100.0, 2) if self.max_storage_gb > 0 else 0.0,
        }

"""Unified Evidence Store for ASTRA-EA.

Acts as the canonical, authoritative repository for evidence artifacts:
- High-resolution keyframe snapshots (.jpg)
- Micro-interaction video clips (.mp4)
- Structured multi-factor evidence evaluations (.json)
- Atomic foreign-key references to SQLite audit records and causal event graphs.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from core.common.logging import get_logger
from core.evidence.types import EvidenceBundle

logger = get_logger("EVIDENCE_STORE")


class UnifiedEvidenceStore:
    """Canonical repository managing evidence files and metadata."""

    def __init__(self, base_dir: str = "data/evidence") -> None:
        self.base_dir = Path(base_dir)
        self.snapshots_dir = self.base_dir / "snapshots"
        self.clips_dir = self.base_dir / "clips"
        self.metadata_dir = self.base_dir / "metadata"

        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        evidence_id: str,
        image: np.ndarray,
        run_id: Optional[str] = None,
        annotations: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """Save evidence frame snapshot to disk."""
        filename = f"{evidence_id}.jpg"
        out_path = self.snapshots_dir / filename

        # Optionally draw annotations if provided
        draw_img = image.copy()
        if annotations:
            for ann in annotations:
                bbox = ann.get("bbox")
                label = ann.get("label", "")
                if bbox and len(bbox) == 4:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    cv2.rectangle(draw_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    if label:
                        cv2.putText(
                            draw_img,
                            label,
                            (x1, max(15, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            1,
                        )

        cv2.imwrite(str(out_path), draw_img)
        logger.debug("Saved evidence snapshot: %s", out_path)
        return out_path

    def save_evidence_bundle(
        self,
        evidence_id: str,
        bundle: EvidenceBundle,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        activity_ref: Optional[str] = None,
    ) -> Path:
        """Serialize structured evidence bundle to JSON metadata."""
        out_path = self.metadata_dir / f"{evidence_id}.json"
        data = {
            "evidence_id": evidence_id,
            "run_id": run_id,
            "step_id": step_id,
            "activity_ref": activity_ref,
            "timestamp": time.time(),
            "bundle": bundle.to_dict(),
        }
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        return out_path

    def get_snapshot_path(self, evidence_id: str) -> Optional[Path]:
        """Return path to snapshot if it exists."""
        p = self.snapshots_dir / f"{evidence_id}.jpg"
        return p if p.exists() else None

    def get_metadata(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored evidence bundle metadata."""
        p = self.metadata_dir / f"{evidence_id}.json"
        if not p.exists():
            return None
        with open(p, "r") as f:
            return json.load(f)

    def list_evidence(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all stored evidence records, optionally filtered by run ID."""
        records = []
        for meta_file in sorted(self.metadata_dir.glob("*.json")):
            try:
                with open(meta_file, "r") as f:
                    meta = json.load(f)
                if run_id is None or meta.get("run_id") == run_id:
                    records.append(meta)
            except Exception:
                pass
        return records

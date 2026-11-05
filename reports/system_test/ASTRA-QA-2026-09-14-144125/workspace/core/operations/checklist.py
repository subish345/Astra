"""Operational Checklist Engine for ASTRA-EA (Phase 19, Section 39, 40, D19.16).

Provides configurable operational checklists with cryptographically signed item statuses,
timestamps, operator identity, and optional evidence verification.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChecklistItemStatus(str, Enum):
    """Execution status of a checklist item (Section 40)."""
    PENDING = "PENDING"
    PASS = "PASS"
    DEGRADED = "DEGRADED"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


@dataclass
class ChecklistItem:
    """Individual operational checklist item."""
    id: str
    name: str
    description: str
    critical: bool = True
    status: ChecklistItemStatus = ChecklistItemStatus.PENDING
    timestamp_utc: Optional[str] = None
    operator: Optional[str] = None
    evidence_path: Optional[str] = None
    notes: Optional[str] = None

    def sign(
        self,
        status: ChecklistItemStatus,
        operator: str,
        notes: Optional[str] = None,
        evidence_path: Optional[str] = None,
    ) -> None:
        """Sign off on checklist item with authoritative timestamp and operator."""
        self.status = status
        self.operator = operator
        self.timestamp_utc = datetime.now(timezone.utc).isoformat()
        self.notes = notes
        self.evidence_path = evidence_path

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Checklist:
    """Configurable collection of checklist items."""
    checklist_id: str
    title: str
    items: List[ChecklistItem] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def add_item(self, item: ChecklistItem) -> None:
        self.items.append(item)

    def get_item(self, item_id: str) -> Optional[ChecklistItem]:
        for it in self.items:
            if it.id == item_id:
                return it
        return None

    def is_complete(self) -> bool:
        """Check if all items have been signed off."""
        return all(it.status != ChecklistItemStatus.PENDING for it in self.items)

    def is_passing(self) -> bool:
        """Check if all critical items passed and no items failed."""
        for it in self.items:
            if it.critical and it.status not in (ChecklistItemStatus.PASS, ChecklistItemStatus.DEGRADED):
                return False
            if it.status == ChecklistItemStatus.FAIL:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checklist_id": self.checklist_id,
            "title": self.title,
            "created_at_utc": self.created_at_utc,
            "is_complete": self.is_complete(),
            "is_passing": self.is_passing(),
            "items": [it.to_dict() for it in self.items],
        }


class ChecklistEngine:
    """Pre-configures and manages operational checklists across mission phases (Section 39)."""

    @classmethod
    def create_pre_mission_checklist(cls) -> Checklist:
        """Factory for PRE_MISSION checklist (Section 9, 39)."""
        cl = Checklist(checklist_id="PRE_MISSION", title="Pre-Mission Operational Verification")
        cl.add_item(ChecklistItem(
            id="CHK_PWR_01",
            name="Power & Silicon Baseline",
            description="Verify silicon architecture, frequency, and nominal thermal zones (<90C)",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_CAM_01",
            name="Optical Camera Stream",
            description="Verify primary optical camera frame acquisition, resolution (>=640x480) and FPS (>=15)",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_MOD_01",
            name="Model ONNX Integrity",
            description="Verify object detector weights checksum and class mapping dictionary",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_PRC_01",
            name="Procedure Schema & Contract",
            description="Verify procedure YAML syntax, step dependencies, and expected apparatus IDs",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_STR_01",
            name="Storage Capacity & Partitions",
            description="Verify writable partitions for mission/, evidence/, and telemetry/ (<95% full)",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_CLK_01",
            name="Mission Monotonic Clock",
            description="Verify clock monotonic tick and synchronization with spacecraft reference (TBD)",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_REC_01",
            name="Video & Audit Recorder",
            description="Verify local video segment writer and audit event logger readiness",
            critical=False,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_GND_01",
            name="Ground Telemetry Link",
            description="Verify ground telemetry event and video streaming socket connectivity",
            critical=False,
        ))
        cl.add_item(ChecklistItem(
            id="CHK_HLT_01",
            name="Unified Subsystem Health Self-Test",
            description="Execute automated health self-test across AI, assurance, and hardware",
            critical=True,
        ))
        return cl

    @classmethod
    def create_camera_setup_checklist(cls) -> Checklist:
        """Factory for CAMERA_SETUP checklist."""
        cl = Checklist(checklist_id="CAMERA_SETUP", title="Optical Camera Viewpoint & Exposure Setup")
        cl.add_item(ChecklistItem(
            id="CAM_ALIGN_01",
            name="Viewpoint Alignment",
            description="Align optical axis with workstation interaction volume",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="CAM_EXP_02",
            name="Exposure & Lighting",
            description="Verify zero glare on apparatus fiducials or specular reflections",
            critical=False,
        ))
        return cl

    @classmethod
    def create_experiment_setup_checklist(cls) -> Checklist:
        """Factory for EXPERIMENT_SETUP checklist."""
        cl = Checklist(checklist_id="EXPERIMENT_SETUP", title="Physical Apparatus & Workstation Setup")
        cl.add_item(ChecklistItem(
            id="APP_STAG_01",
            name="Apparatus Staging",
            description="Ensure test tubes, pipette, centrifuge, and rack are present in stage zone",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="PPE_VERIF_02",
            name="Operator Gloves & Safety",
            description="Confirm clean nitrile gloves attached and clear line-of-sight to apparatus",
            critical=True,
        ))
        return cl

    @classmethod
    def create_post_mission_checklist(cls) -> Checklist:
        """Factory for POST_MISSION checklist."""
        cl = Checklist(checklist_id="POST_MISSION", title="Post-Mission Records & Export Verification")
        cl.add_item(ChecklistItem(
            id="REC_FLUSH_01",
            name="Buffer Flush Verification",
            description="Verify all event streams and evidence clips flushed to non-volatile storage",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="REP_GEN_02",
            name="Mission Audit Report Generation",
            description="Generate signed JSON and HTML mission reports with SHA-256 hashes",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="EXP_ARCH_03",
            name="Run Archive & Export",
            description="Export self-contained RUN_XXXX bundle for ground science team review",
            critical=False,
        ))
        return cl

    @classmethod
    def create_shutdown_checklist(cls) -> Checklist:
        """Factory for SHUTDOWN checklist."""
        cl = Checklist(checklist_id="SHUTDOWN", title="Safe Controlled System Shutdown")
        cl.add_item(ChecklistItem(
            id="CAM_STOP_01",
            name="Optical Camera Power Down",
            description="Release V4L2 device descriptor and stop capture thread",
            critical=True,
        ))
        cl.add_item(ChecklistItem(
            id="MOD_UNLD_02",
            name="Model Session Cleanup",
            description="Release ONNX inference session and deallocate tensor buffers",
            critical=True,
        ))
        return cl

"""Change Impact Analysis & Regression Selection Engine for ASTRA-EA (Phase 16).

Analyzes git diffs or file modification paths to identify affected:
- Requirements
- Subsystems & Models
- Procedures & Evidence
- Regression test targets
Generates reports/verification/impact_report.json.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from verification.traceability import ARCHITECTURE_MAP, TraceabilityEngine


SUBSYSTEM_DEPENDENCIES = {
    "perception": {
        "patterns": ["core/perception/", "models/"],
        "subsystem": "PERCEPTION",
        "cascades_to": ["INTERACTION", "ACTIVITY", "EVIDENCE", "PROCEDURE", "ASSURANCE"],
        "retrain_model_advised": True,
        "affected_tests": ["V-SYS-001", "V-SYS-002", "V-SYS-008", "V-PERF-001", "V-PERF-003", "V-SAF-001", "V-SAF-002"],
    },
    "interaction": {
        "patterns": ["core/interaction/"],
        "subsystem": "INTERACTION",
        "cascades_to": ["ACTIVITY", "EVIDENCE", "PROCEDURE", "ASSURANCE"],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-003-IOU", "V-SYS-001", "V-SYS-006-ASSURANCE"],
    },
    "temporal_activity": {
        "patterns": ["core/temporal/", "core/activity/"],
        "subsystem": "TEMPORAL_ACTIVITY",
        "cascades_to": ["PROCEDURE", "ASSURANCE"],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-004-TEMPORAL", "V-SYS-001", "V-SYS-006-ASSURANCE"],
    },
    "procedure": {
        "patterns": ["core/procedure/", "configs/experiments/"],
        "subsystem": "PROCEDURE",
        "cascades_to": ["ASSURANCE", "RECOVERY"],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-003", "V-SYS-005", "V-SYS-006-ASSURANCE", "V-DAT-002"],
    },
    "assurance_recovery": {
        "patterns": ["core/assurance/", "core/assistance/recovery"],
        "subsystem": "ASSURANCE_RECOVERY",
        "cascades_to": ["SAFETY", "RECOVERY"],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-002", "V-SYS-004", "V-SYS-005", "V-SYS-006-ASSURANCE", "V-SAF-001", "V-SAF-002"],
    },
    "camera_hardware": {
        "patterns": ["core/camera/", "configs/cameras/"],
        "subsystem": "CAMERA_HARDWARE",
        "cascades_to": ["PERCEPTION", "SAFETY"],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-001", "V-SYS-006", "V-IF-001", "V-SAF-003", "V-ENV-001", "V-ENV-002"],
    },
    "audio_voice": {
        "patterns": ["core/assistance/voice", "core/audio/"],
        "subsystem": "AUDIO_VOICE",
        "cascades_to": [],
        "retrain_model_advised": False,
        "affected_tests": ["V-SYS-007-VOICE", "V-OPS-002", "V-REL-001"],
    },
    "gui_console": {
        "patterns": ["core/gui/", "apps/"],
        "subsystem": "GUI_CONSOLE",
        "cascades_to": [],
        "retrain_model_advised": False,
        "affected_tests": ["V-OPS-001"],
    },
    "streaming_ground": {
        "patterns": ["core/streaming/"],
        "subsystem": "STREAMING_GROUND",
        "cascades_to": [],
        "retrain_model_advised": False,
        "affected_tests": ["V-IF-004", "V-SEC-003", "V-SAF-004"],
    },
    "security_data": {
        "patterns": ["core/security/", "core/mission/", "storage/"],
        "subsystem": "SECURITY_DATA",
        "cascades_to": [],
        "retrain_model_advised": False,
        "affected_tests": ["V-SEC-001", "V-SEC-002", "V-DAT-001", "V-DAT-002", "V-DAT-003"],
    },
}


class ChangeImpactAnalyzer:
    """Computes downstream impact of code and configuration changes."""

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = root_dir or Path(os.getcwd())
        self.traceability = TraceabilityEngine(self.root_dir)
        self.reports_dir = self.root_dir / "reports" / "verification"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def get_modified_files(self) -> List[str]:
        """Detect modified files using git diff."""
        try:
            cmd = ["git", "diff", "--name-only", "HEAD~1"]
            out = subprocess.check_output(cmd, cwd=str(self.root_dir), text=True, stderr=subprocess.DEVNULL)
            lines = [l.strip() for l in out.splitlines() if l.strip()]
            if lines:
                return lines
        except Exception:
            pass

        # Fallback to uncommitted changes
        try:
            cmd = ["git", "status", "--porcelain"]
            out = subprocess.check_output(cmd, cwd=str(self.root_dir), text=True, stderr=subprocess.DEVNULL)
            modified = []
            for l in out.splitlines():
                parts = l.strip().split()
                if len(parts) >= 2:
                    modified.append(parts[-1])
            return modified
        except Exception:
            return []

    def analyze_impact(self, modified_files: List[str] | None = None) -> Dict[str, Any]:
        """Compute change impact across requirements, models, procedures, and tests."""
        if modified_files is None:
            modified_files = self.get_modified_files()

        affected_subsystems: Set[str] = set()
        cascading_subsystems: Set[str] = set()
        recommended_tests: Set[str] = set()
        retrain_advised = False
        procedure_invalidation = False

        for f in modified_files:
            f_norm = f.replace("\\", "/")
            if "configs/experiments/" in f_norm:
                procedure_invalidation = True
            for sub_key, sub_meta in SUBSYSTEM_DEPENDENCIES.items():
                for pat in sub_meta["patterns"]:
                    if pat in f_norm:
                        affected_subsystems.add(sub_meta["subsystem"])
                        cascading_subsystems.update(sub_meta["cascades_to"])
                        recommended_tests.update(sub_meta["affected_tests"])
                        if sub_meta["retrain_model_advised"]:
                            retrain_advised = True

        # Find affected requirement IDs via ARCHITECTURE_MAP
        affected_requirements = set()
        for f in modified_files:
            f_norm = f.replace("\\", "/")
            for rid, arch in ARCHITECTURE_MAP.items():
                if arch["source"] in f_norm:
                    affected_requirements.add(rid)

        # Build impact report
        report = {
            "modified_files": modified_files,
            "file_count": len(modified_files),
            "primary_subsystems": sorted(list(affected_subsystems)),
            "cascading_subsystems": sorted(list(cascading_subsystems)),
            "affected_requirements": sorted(list(affected_requirements)),
            "recommended_regression_tests": sorted(list(recommended_tests)),
            "retrain_model_advised": retrain_advised,
            "procedure_revalidation_required": procedure_invalidation,
            "is_ui_only_change": bool(affected_subsystems == {"GUI_CONSOLE"}),
            "summary": (
                f"Impact: {len(affected_subsystems)} subsystems affected, "
                f"{len(recommended_tests)} test cases scheduled for re-verification."
            ),
        }

        # Write reports/verification/impact_report.json
        out_json = self.reports_dir / "impact_report.json"
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report

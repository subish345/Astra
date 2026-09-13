# ==============================================================================
# ASTRA-EA Hardening Manager (Phase 21, D21.01, D21.03)
# Autonomous Spacecraft Experiment Assurance & Assistance (SIH26174)
# ==============================================================================
"""Orchestrates findings tracking, root cause analyses, corrective actions,

and release readiness gating for Release Candidate 2 (RC2).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.common.config import get_project_root


@dataclass
class HardeningFinding:
    """Formal finding record (Section 5)."""
    id: str
    title: str
    source: str
    date: str
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW | OBSERVATION
    category: str        # CAMERA | PERCEPTION | RECOVERY | UI | GROUND | STORAGE | etc.
    description: str
    evidence: List[str] = field(default_factory=list)
    impact: str = ""
    status: str = "OPEN" # OPEN | ANALYZED | FIXED | RETEST | CLOSED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HardeningManager:
    """Manages Phase 21 findings, RCA traceability, and release candidate qualification."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or get_project_root()
        self.hardening_dir = self.root / "hardening"
        self.findings_dir = self.hardening_dir / "findings"
        self.root_cause_dir = self.hardening_dir / "root-cause"
        self.actions_dir = self.hardening_dir / "actions"
        self.impact_dir = self.hardening_dir / "impact"
        self.reports_dir = self.root / "reports" / "hardening"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def load_findings(self) -> List[HardeningFinding]:
        """Load all registered findings from YAML files in hardening/findings/."""
        findings: List[HardeningFinding] = []
        if not self.findings_dir.exists():
            return findings

        for f_path in sorted(self.findings_dir.glob("FINDING-*.yaml")):
            try:
                with open(f_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "id" in data:
                    findings.append(HardeningFinding(**data))
            except Exception:
                pass
        return findings

    def get_finding(self, finding_id: str) -> Optional[HardeningFinding]:
        """Fetch single finding by ID."""
        for f in self.load_findings():
            if f.id.upper() == finding_id.upper():
                return f
        return None

    def get_root_cause(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Fetch Root Cause Analysis for a finding."""
        rca_file = self.root_cause_dir / f"RCA-{finding_id.upper()}.yaml"
        if rca_file.is_file():
            with open(rca_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return None

    def get_action(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Fetch Corrective Action (CAPA) associated with a finding."""
        if not self.actions_dir.exists():
            return None
        for a_file in self.actions_dir.glob("CAPA-*.yaml"):
            try:
                with open(a_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and data.get("finding_id", "").upper() == finding_id.upper():
                    return data
            except Exception:
                pass
        return None

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Compute aggregate metrics across all findings (Section 43)."""
        findings = self.load_findings()
        counts_by_severity = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "OBSERVATION": 0}
        counts_by_status = {"OPEN": 0, "ANALYZED": 0, "FIXED": 0, "RETEST": 0, "CLOSED": 0}

        for f in findings:
            sev = f.severity.upper()
            st = f.status.upper()
            if sev in counts_by_severity:
                counts_by_severity[sev] += 1
            if st in counts_by_status:
                counts_by_status[st] += 1

        return {
            "total_findings": len(findings),
            "by_severity": counts_by_severity,
            "by_status": counts_by_status,
            "open_critical": sum(1 for f in findings if f.severity == "CRITICAL" and f.status != "CLOSED"),
            "open_high": sum(1 for f in findings if f.severity == "HIGH" and f.status != "CLOSED"),
            "readiness_verdict": "READY" if (counts_by_severity["CRITICAL"] == 0 or all(f.status == "CLOSED" for f in findings if f.severity in ("CRITICAL", "HIGH"))) else "BLOCKED",
        }

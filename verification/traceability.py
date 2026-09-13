"""Automated Traceability Engine & Orphan Detection for ASTRA-EA (Phase 16).

Transforms:
Requirement -> Design Component -> Source Module -> Test Case -> Execution -> Evidence -> Result

Calculates Verification Coverage, Evidence Coverage, and detects orphan entities.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import yaml

from verification.test_registry import TestRegistry


# Static architecture map connecting requirements to design components and implementation source files
ARCHITECTURE_MAP: Dict[str, Dict[str, str]] = {
    "ASTRA-SYS-001": {"design": "Optical Ingestion", "source": "core/camera/webcam.py"},
    "ASTRA-SYS-002": {"design": "Neural Perception", "source": "core/perception/detector.py"},
    "ASTRA-SYS-003": {"design": "Spatial Interaction", "source": "core/interaction/geometry.py"},
    "ASTRA-SYS-004": {"design": "Temporal Activity Dwell", "source": "core/temporal/buffer.py"},
    "ASTRA-SYS-005": {"design": "Deterministic Procedure Tracking", "source": "core/procedure/progress.py"},
    "ASTRA-SYS-006": {"design": "Tri-State Assurance", "source": "core/assurance/engine.py"},
    "ASTRA-SYS-007": {"design": "Cockpit Voice & HUD Guidance", "source": "core/assistance/voice.py"},
    "ASTRA-SYS-008": {"design": "Closed-Loop Recovery", "source": "core/assistance/recovery.py"},
    "ASTRA-PERF-001": {"design": "High-Throughput Scheduler", "source": "core/optimization/scheduler.py"},
    "ASTRA-PERF-002": {"design": "Latency Control Loop", "source": "core/procedure/benchmark.py"},
    "ASTRA-PERF-003": {"design": "Edge Neural Runtime", "source": "core/optimization/runtime.py"},
    "ASTRA-PERF-004": {"design": "Memory Stability Manager", "source": "core/optimization/soak.py"},
    "ASTRA-PERF-005": {"design": "Cold-Boot Initializer", "source": "core/cli/commands.py"},
    "ASTRA-IF-001": {"design": "V4L2 Ingestion & Device Monitor", "source": "core/camera/device_manager.py"},
    "ASTRA-IF-002": {"design": "Vehicle Bus Abstraction", "source": "core/integration/bus.py"},
    "ASTRA-IF-003": {"design": "Dual Monotonic/UTC Time Sync", "source": "core/mission/database.py"},
    "ASTRA-IF-004": {"design": "Non-Blocking Telemetry Server", "source": "core/streaming/event_server.py"},
    "ASTRA-SAF-001": {"design": "Epistemic Non-Guessing Barrier", "source": "core/assurance/engine.py"},
    "ASTRA-SAF-002": {"design": "Occlusion Observation Window", "source": "core/assurance/engine.py"},
    "ASTRA-SAF-003": {"design": "Ingestion Dropout Watchdog", "source": "core/camera/device_manager.py"},
    "ASTRA-SAF-004": {"design": "Auxiliary Subsystem Isolation", "source": "core/assistance/voice.py"},
    "ASTRA-REL-001": {"design": "Subsystem Failure Containment", "source": "core/system/orchestrator.py"},
    "ASTRA-REL-002": {"design": "Heuristic Detector Fallback", "source": "core/perception/color_detector.py"},
    "ASTRA-REL-003": {"design": "Formal Degraded Modes", "source": "docs/qualification/degraded-modes.md"},
    "ASTRA-SEC-001": {"design": "Air-Gapped Execution Enforcer", "source": "core/security/airgap.py"},
    "ASTRA-SEC-002": {"design": "Cryptographic Checksum Verifier", "source": "competition/CHECKSUMS/SHA256SUMS"},
    "ASTRA-SEC-003": {"design": "Read-Only Ground Endpoint Guard", "source": "core/streaming/security.py"},
    "ASTRA-DAT-001": {"design": "SQLite WAL Microsecond Logger", "source": "core/mission/database.py"},
    "ASTRA-DAT-002": {"design": "Causal Decision Provenance", "source": "core/procedure/traceability.py"},
    "ASTRA-DAT-003": {"design": "Bounded Storage Rate Limiter", "source": "storage/storage_manager.py"},
    "ASTRA-OPS-001": {"design": "High-Contrast Cockpit HUD", "source": "core/gui/console.py"},
    "ASTRA-OPS-002": {"design": "Speech Articulation Rate Controller", "source": "core/assistance/voice.py"},
    "ASTRA-OPS-003": {"design": "Pre-Flight Self-Test Diagnostician", "source": "core/cli/commands.py"},
    "ASTRA-ENV-001": {"design": "Photometric Dynamic Range Handler", "source": "core/camera/profile.py"},
    "ASTRA-ENV-002": {"design": "Multi-Angle Viewpoint Invariance", "source": "core/camera/profile.py"},
    "ASTRA-ENV-003": {"design": "Launch Vibration Structural Isolation", "source": "docs/qualification/environmental-test-plan.md"},
    "ASTRA-ENV-004": {"design": "Conductive Thermal Vacuum Path", "source": "docs/qualification/environmental-test-plan.md"},
    "ASTRA-ENV-005": {"design": "TID Radiation Mitigation & ECC", "source": "docs/qualification/environmental-test-plan.md"},
}


class TraceabilityEngine:
    """Computes full traceability matrices, calculates coverage metrics, and detects defects."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(os.getcwd())
        self.registry = TestRegistry(self.root_dir)
        self.reports_dir = self.root_dir / "reports" / "verification"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def build_traceability_matrix(self) -> List[Dict[str, Any]]:
        """Build the full Requirement -> Design -> Source -> Test -> Result -> Evidence graph."""
        matrix = []
        reqs = self.registry.requirements
        tests_by_req: Dict[str, List[str]] = {}
        for tid, tc in self.registry.test_cases.items():
            rid = tc.get("requirement", "")
            tests_by_req.setdefault(rid, []).append(tid)

        for rid, req in sorted(reqs.items()):
            arch = ARCHITECTURE_MAP.get(rid, {"design": "Core Architecture", "source": "core/system/"})
            assigned_tests = tests_by_req.get(rid, [])
            
            # If multiple tests exist, collect them
            test_names = ", ".join(assigned_tests) if assigned_tests else "NONE"
            
            # Determine overall verification result
            results = []
            evidences = set()
            for tid in assigned_tests:
                rec = self.registry.records.get(tid)
                if rec:
                    results.append(rec.get("result", "UNKNOWN"))
                    for ev in rec.get("evidence", []):
                        evidences.add(ev)
                else:
                    results.append("UNEXECUTED")

            # Determine primary status
            if "FAIL" in results:
                agg_result = "FAIL"
            elif "PARTIAL" in results:
                agg_result = "PARTIAL"
            elif "DEFERRED" in results:
                agg_result = "DEFERRED"
            elif all(r == "PASS" for r in results) and results:
                agg_result = "PASS"
            else:
                agg_result = "UNVERIFIED"

            matrix.append({
                "requirement_id": rid,
                "title": req.get("title", ""),
                "category": req.get("category", "SYSTEM"),
                "status": req.get("status", "DRAFT"),
                "verification_method": req.get("verification_method", []),
                "verification_level": req.get("verification_level", "SYSTEM"),
                "design_component": arch["design"],
                "source_module": arch["source"],
                "test_ids": assigned_tests,
                "test_display": test_names,
                "result": agg_result,
                "evidence": sorted(list(evidences)) if evidences else req.get("evidence", []),
            })
        return matrix

    def check_traceability_orphans(self) -> Dict[str, List[str]]:
        """Detect traceability defects:
        - requirements with no test
        - tests with no requirement
        - evidence with no test
        - tests with no result
        - failed tests marked verified
        """
        matrix = self.build_traceability_matrix()
        req_ids = set(self.registry.requirements.keys())
        test_req_ids = {tc.get("requirement") for tc in self.registry.test_cases.values()}
        
        # 1. Requirements with no test
        reqs_no_test = [rid for rid in req_ids if rid not in test_req_ids]

        # 2. Tests with no requirement
        tests_no_req = [
            tid for tid, tc in self.registry.test_cases.items()
            if not tc.get("requirement") or tc.get("requirement") not in req_ids
        ]

        # 3. Tests with no result
        tests_no_result = [
            tid for tid in self.registry.test_cases
            if tid not in self.registry.records
        ]

        # 4. Failed tests marked verified
        failed_marked_verified = []
        for entry in matrix:
            if entry["result"] == "FAIL" and entry["status"] in ["VERIFIED", "VALIDATED"]:
                failed_marked_verified.append(entry["requirement_id"])

        # 5. Evidence with no test
        evidence_files = set()
        ev_dir = self.root_dir / "verification" / "evidence"
        if ev_dir.exists():
            for p in ev_dir.glob("*"):
                if p.name != "manifest.json" and p.is_file():
                    evidence_files.add(str(p.relative_to(self.root_dir)))

        referenced_evidence = set()
        for tc in self.registry.test_cases.values():
            for ev in tc.get("evidence", []):
                referenced_evidence.add(ev)

        evidence_no_test = [ev for ev in evidence_files if ev not in referenced_evidence]

        return {
            "requirements_with_no_test": reqs_no_test,
            "tests_with_no_requirement": tests_no_req,
            "tests_with_no_result": tests_no_result,
            "failed_tests_marked_verified": failed_marked_verified,
            "evidence_with_no_test": evidence_no_test,
        }

    def compute_metrics(self) -> Dict[str, Any]:
        """Calculate formal V&V coverage metrics according to Sections 14 & 15."""
        matrix = self.build_traceability_matrix()
        total_reqs = len(matrix)
        
        # Applicable requirements (exclude DEFERRED environmental qualification tests for ground metrics)
        applicable_reqs = [r for r in matrix if r["status"] != "DEFERRED"]
        applicable_count = len(applicable_reqs)

        verified_reqs = [r for r in applicable_reqs if r["status"] == "VERIFIED"]
        validated_reqs = [r for r in applicable_reqs if r["status"] == "VALIDATED"]
        partial_reqs = [r for r in applicable_reqs if r["status"] == "PARTIAL"]
        blocked_reqs = [r for r in applicable_reqs if r["status"] == "BLOCKED"]
        deferred_reqs = [r for r in matrix if r["status"] == "DEFERRED"]
        unverified_reqs = [
            r for r in applicable_reqs
            if r["status"] not in ["VERIFIED", "VALIDATED", "PARTIAL", "BLOCKED"]
        ]

        verified_and_validated_count = len(verified_reqs) + len(validated_reqs)
        
        # Requirements with linked and existing evidence
        reqs_with_evidence = []
        for r in applicable_reqs:
            if r["evidence"]:
                # Check at least one evidence artifact exists
                has_existing = any((self.root_dir / ev).exists() for ev in r["evidence"])
                if has_existing:
                    reqs_with_evidence.append(r)

        verification_coverage = (verified_and_validated_count / applicable_count * 100.0) if applicable_count else 0.0
        evidence_coverage = (len(reqs_with_evidence) / applicable_count * 100.0) if applicable_count else 0.0

        orphans = self.check_traceability_orphans()

        return {
            "total_requirements": total_reqs,
            "applicable_requirements": applicable_count,
            "verified": len(verified_reqs),
            "validated": len(validated_reqs),
            "partial": len(partial_reqs),
            "blocked": len(blocked_reqs),
            "deferred": len(deferred_reqs),
            "unverified": len(unverified_reqs),
            "requirements_with_evidence": len(reqs_with_evidence),
            "verification_coverage_percent": round(verification_coverage, 1),
            "evidence_coverage_percent": round(evidence_coverage, 1),
            "orphans": orphans,
            "orphan_free": all(len(v) == 0 for v in orphans.values()),
        }

    def render_ascii_table(self) -> str:
        """Render standard ASCII traceability table matching Section 13."""
        matrix = self.build_traceability_matrix()
        lines = []
        lines.append(f"{'Requirement':<18} {'Implementation':<32} {'Test':<18} {'Result'}")
        lines.append("-" * 78)
        for r in matrix:
            req_id = r["requirement_id"]
            src = Path(r["source_module"]).name
            test_str = r["test_ids"][0] if r["test_ids"] else "NONE"
            lines.append(f"{req_id:<18} {src:<32} {test_str:<18} {r['result']}")
        return "\n".join(lines)

    def generate_traceability_html(self) -> Path:
        """Generate reports/verification/traceability.html report."""
        matrix = self.build_traceability_matrix()
        metrics = self.compute_metrics()
        orphans = metrics["orphans"]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Formal Requirements Traceability Matrix</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #0a0f1d; color: #e2e8f0; }}
        h1, h2 {{ color: #38bdf8; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
        .metric-card {{ background: #1e293b; padding: 1.25rem; border-radius: 8px; border: 1px solid #334155; }}
        .metric-val {{ font-size: 2rem; font-weight: bold; color: #38bdf8; }}
        .badge-pass {{ background: #065f46; color: #34d399; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}
        .badge-deferred {{ background: #78350f; color: #fde047; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}
        .badge-fail {{ background: #7f1d1d; color: #f87171; padding: 3px 8px; border-radius: 4px; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; background: #0f172a; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 0.88rem; }}
        th {{ background: #1e293b; color: #94a3b8; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }}
        tr:hover {{ background: #1e293b44; }}
        code {{ background: #1e293b; padding: 2px 6px; border-radius: 4px; color: #7dd3fc; }}
    </style>
</head>
<body>
    <h1>ASTRA-EA — Formal Requirements Traceability Matrix (Phase 16)</h1>
    <p>Standard: ECSS-E-ST-40C / NASA-STD-8739.8 | Milestone: Phase 16 Formal V&V</p>

    <div class="metric-grid">
        <div class="metric-card">
            <div>Total Requirements</div>
            <div class="metric-val">{metrics['total_requirements']}</div>
        </div>
        <div class="metric-card">
            <div>Verification Coverage</div>
            <div class="metric-val">{metrics['verification_coverage_percent']}%</div>
        </div>
        <div class="metric-card">
            <div>Evidence Coverage</div>
            <div class="metric-val">{metrics['evidence_coverage_percent']}%</div>
        </div>
        <div class="metric-card">
            <div>Traceability Orphans</div>
            <div class="metric-val">{'0 (CLEAN)' if metrics['orphan_free'] else 'DETECTED'}</div>
        </div>
    </div>

    <h2>End-to-End Requirement-to-Evidence Matrix</h2>
    <table>
        <thead>
            <tr>
                <th>Req ID</th>
                <th>Title</th>
                <th>Category</th>
                <th>Design Component</th>
                <th>Source Module</th>
                <th>Formal Test Case</th>
                <th>Result</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
"""
        for r in matrix:
            badge_class = "badge-pass" if r["result"] in ["PASS", "VERIFIED", "VALIDATED"] else ("badge-deferred" if r["result"] == "DEFERRED" else "badge-fail")
            html += f"""            <tr>
                <td><strong><code>{r['requirement_id']}</code></strong></td>
                <td>{r['title']}</td>
                <td>{r['category']}</td>
                <td>{r['design_component']}</td>
                <td><code>{r['source_module']}</code></td>
                <td><code>{r['test_display']}</code></td>
                <td><span class="{badge_class}">{r['result']}</span></td>
                <td><span class="{badge_class}">{r['status']}</span></td>
            </tr>\n"""

        html += """        </tbody>
    </table>
</body>
</html>"""

        out_path = self.reports_dir / "traceability.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        return out_path

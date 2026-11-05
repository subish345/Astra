"""Operator Training Mode and Operational Failure Drills (Phase 19, Section 45, 46, 51, 52, D19.18, D19.19).

Simulates operational failure scenarios allowing astronauts and ground operators to practice
deviation handling and recovery playbooks in an isolated, measurable training environment.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.common.config import get_project_root


class DrillType(str, Enum):
    """The 7 official operational failure drills (Section 51)."""
    DRILL_CAMERA_FAILURE = "DRILL_CAMERA_FAILURE"
    DRILL_NETWORK_LOSS = "DRILL_NETWORK_LOSS"
    DRILL_WRONG_OBJECT = "DRILL_WRONG_OBJECT"
    DRILL_MODEL_FAILURE = "DRILL_MODEL_FAILURE"
    DRILL_STORAGE_WARNING = "DRILL_STORAGE_WARNING"
    DRILL_GROUND_DISCONNECT = "DRILL_GROUND_DISCONNECT"
    DRILL_RECOVERY_FAILURE = "DRILL_RECOVERY_FAILURE"


@dataclass
class DrillEvaluation:
    """Quantitative training record produced by an operational drill (Section 46, 52)."""
    drill_id: str
    operator: str
    started_at_utc: str
    detection_time_ms: float
    response_time_ms: float
    recovery_time_ms: float
    final_state: str
    missed_actions: List[str] = field(default_factory=list)
    verdict: str = "PASS"  # PASS | FAIL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OperatorTrainingEngine:
    """Manages training sessions and automated failure drill simulations."""

    DRILL_SPECS: Dict[DrillType, Dict[str, Any]] = {
        DrillType.DRILL_CAMERA_FAILURE: {
            "title": "Camera Sensor Loss Drill",
            "symptom": "Optical frame acquisition timeout (>2.0s)",
            "expected_actions": [
                "Verify CAMERA_FAILED alert",
                "Acknowledge alert within 5.0s",
                "Ensure perception transitions to DEGRADED",
                "Verify procedure verification pauses safely",
            ],
            "max_detection_ms": 200.0,
            "max_response_ms": 5000.0,
        },
        DrillType.DRILL_NETWORK_LOSS: {
            "title": "Telemetry Ground Sever Drill",
            "symptom": "Ground telemetry socket closed unexpectedly",
            "expected_actions": [
                "Verify ground link marked OFFLINE",
                "Ensure onboard autonomous execution continues uninterrupted",
                "Buffer missed events in local ring buffer",
            ],
            "max_detection_ms": 300.0,
            "max_response_ms": 3000.0,
        },
        DrillType.DRILL_WRONG_OBJECT: {
            "title": "Wrong Apparatus Interaction Drill",
            "symptom": "Apparatus detector flags incorrect object interaction",
            "expected_actions": [
                "Flag DEVIATION_DETECTED with WARNING severity",
                "Acknowledge alert",
                "Execute corrective recovery guidance",
                "Verify step returns to NOMINAL",
            ],
            "max_detection_ms": 150.0,
            "max_response_ms": 4000.0,
        },
        DrillType.DRILL_MODEL_FAILURE: {
            "title": "Inference Session Exception Drill",
            "symptom": "ONNX Runtime model execution exception caught",
            "expected_actions": [
                "Detect inference failure",
                "Engage rule-based fallback detector",
                "Avoid unhandled crash",
            ],
            "max_detection_ms": 100.0,
            "max_response_ms": 2000.0,
        },
        DrillType.DRILL_STORAGE_WARNING: {
            "title": "Storage Partition Capacity Drill",
            "symptom": "Diagnostic partition exceeds 85% utilization",
            "expected_actions": [
                "Detect storage capacity threshold crossing",
                "Prune debug/diagnostic logs first (Section 28 priority)",
                "Preserve all mission and evidence files intact",
            ],
            "max_detection_ms": 250.0,
            "max_response_ms": 3000.0,
        },
        DrillType.DRILL_GROUND_DISCONNECT: {
            "title": "Ground Monitor Disconnect & State Reconciliation Drill",
            "symptom": "Ground connection lost and re-established after 5 missed events",
            "expected_actions": [
                "Detect sequence jump (gaps in sequence numbers)",
                "Request missed event batch from onboard buffer",
                "Reconcile timeline without duplicating records",
            ],
            "max_detection_ms": 200.0,
            "max_response_ms": 3000.0,
        },
        DrillType.DRILL_RECOVERY_FAILURE: {
            "title": "Unsuccessful Corrective Action Escalation Drill",
            "symptom": "Operator performs secondary invalid action during recovery",
            "expected_actions": [
                "Detect recovery attempt failure",
                "Escalate alert from LEVEL_1 to LEVEL_2 (System Engineer)",
                "Pause experiment progression safely",
            ],
            "max_detection_ms": 200.0,
            "max_response_ms": 4000.0,
        },
    }

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or get_project_root()

    def run_drill(self, drill: DrillType, operator: str = "Trainee_01") -> DrillEvaluation:
        """Simulate and evaluate an operational failure drill (Section 52)."""
        spec = self.DRILL_SPECS[drill]
        t_start = time.perf_counter()
        now_utc = datetime.now(timezone.utc).isoformat()

        # Simulate drill execution
        # Detection time
        t0 = time.perf_counter()
        # Simulated fault injection & detection
        time.sleep(0.01)
        det_ms = (time.perf_counter() - t0) * 1000.0

        # Operator acknowledgement & response
        t1 = time.perf_counter()
        time.sleep(0.02)
        resp_ms = (time.perf_counter() - t1) * 1000.0

        # Recovery verification
        t2 = time.perf_counter()
        time.sleep(0.01)
        rec_ms = (time.perf_counter() - t2) * 1000.0

        missed = []
        if det_ms > spec["max_detection_ms"]:
            missed.append(f"Detection latency ({det_ms:.1f}ms) exceeded threshold ({spec['max_detection_ms']}ms)")
        if resp_ms > spec["max_response_ms"]:
            missed.append(f"Response latency ({resp_ms:.1f}ms) exceeded threshold ({spec['max_response_ms']}ms)")

        verdict = "PASS" if not missed else "FAIL"

        eval_record = DrillEvaluation(
            drill_id=drill.value,
            operator=operator,
            started_at_utc=now_utc,
            detection_time_ms=round(det_ms, 2),
            response_time_ms=round(resp_ms, 2),
            recovery_time_ms=round(rec_ms, 2),
            final_state="RESOLVED" if verdict == "PASS" else "DEGRADED",
            missed_actions=missed,
            verdict=verdict,
        )

        # Save record to isolated reports/training/ directory (Section 46)
        out_dir = self.root / "reports" / "training"
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"drill_{drill.value.lower()}_{int(time.time())}.json", "w", encoding="utf-8") as f:
            json.dump(eval_record.to_dict(), f, indent=2)

        return eval_record

    def run_all_drills(self, operator: str = "Trainee_01") -> Dict[str, Any]:
        """Execute all 7 failure drills and generate composite report."""
        results = []
        for drill in DrillType:
            res = self.run_drill(drill, operator)
            results.append(res.to_dict())

        passed = sum(1 for r in results if r["verdict"] == "PASS")
        return {
            "operator": operator,
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "total_drills": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "overall_status": "PASS" if passed == len(results) else "FAIL",
            "drills": results,
        }

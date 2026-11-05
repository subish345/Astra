"""Regression Engine for ASTRA-EA (Phase 16).

Executes comprehensive regression sweeps:
- Unit & Component tests
- Integration & Pipeline tests
- Invariant Property tests (tests/properties/)
- System Scenarios (V-SYS-001 through V-SYS-008)
- Performance & Timing audits
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from verification.test_registry import TestRegistry
from verification.traceability import TraceabilityEngine


class RegressionEngine:
    """Automated test execution orchestrator for formal V&V regression."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(os.getcwd())
        self.registry = TestRegistry(self.root_dir)
        self.traceability = TraceabilityEngine(self.root_dir)

    def run_pytest_suite(self, target: str = "tests/") -> Dict[str, Any]:
        """Execute a targeted pytest run and parse results."""
        start = time.perf_counter()
        targets = target.split() if isinstance(target, str) else list(target)
        cmd = [sys.executable, "-m", "pytest"] + targets + ["-q", "--tb=short"]
        proc = subprocess.run(cmd, cwd=str(self.root_dir), capture_output=True, text=True)
        elapsed = time.perf_counter() - start

        passed = proc.returncode == 0
        return {
            "target": target,
            "passed": passed,
            "returncode": proc.returncode,
            "duration_seconds": round(elapsed, 2),
            "stdout": proc.stdout[-800:] if len(proc.stdout) > 800 else proc.stdout,
            "stderr": proc.stderr[-800:] if len(proc.stderr) > 800 else proc.stderr,
        }

    def run_formal_test_cases(self) -> Dict[str, Any]:
        """Execute all formal test cases in the test registry."""
        return self.registry.run_all()

    def run_full_regression(self) -> Dict[str, Any]:
        """Execute full end-to-end regression sweep."""
        print("=" * 60)
        print(" ASTRA-EA FORMAL V&V REGRESSION SWEEP")
        print("=" * 60)

        # 1. Formal Test Case execution
        print("[1/4] Executing Formal Test Cases (V-SYS-001 to V-ENV-005)...")
        tc_results = self.run_formal_test_cases()
        tc_pass = sum(1 for r in tc_results.values() if r["result"] == "PASS")
        tc_def = sum(1 for r in tc_results.values() if r["result"] == "DEFERRED")
        print(f"      Formal Tests: {tc_pass} PASSED, {tc_def} DEFERRED (Planned TRL 6)")

        # 2. Invariant Property Suite
        print("[2/4] Executing Invariant Property Suite (tests/properties/)...")
        prop_res = self.run_pytest_suite("tests/properties/")
        status_str = "PASS" if prop_res["passed"] else "FAIL"
        print(f"      Property Suite: {status_str} in {prop_res['duration_seconds']}s")

        # 3. Unit & Integration Regression
        print("[3/4] Executing Core Unit & Integration Tests (tests/unit/, tests/integration/)...")
        core_res = self.run_pytest_suite("tests/unit/ tests/integration/")
        status_str = "PASS" if core_res["passed"] else "FAIL"
        print(f"      Core Suites: {status_str} in {core_res['duration_seconds']}s")

        # 4. Traceability & Orphan Verification
        print("[4/4] Verifying Traceability & Orphan Status...")
        metrics = self.traceability.compute_metrics()
        orphan_status = "0 (CLEAN)" if metrics["orphan_free"] else "DETECTED"
        print(f"      Traceability: {metrics['verification_coverage_percent']}% Verified, Orphans: {orphan_status}")

        all_passed = (
            prop_res["passed"]
            and core_res["passed"]
            and metrics["orphan_free"]
            and tc_pass >= 30
        )

        print("=" * 60)
        overall_str = "ALL REGRESSION GATES PASSED" if all_passed else "REGRESSION DEFECTS DETECTED"
        print(f" OVERALL STATUS: {overall_str}")
        print("=" * 60)

        return {
            "all_passed": all_passed,
            "test_cases_passed": tc_pass,
            "test_cases_deferred": tc_def,
            "property_suite": prop_res,
            "core_suite": core_res,
            "metrics": metrics,
        }

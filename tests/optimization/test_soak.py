"""Automated tests for Soak Endurance and Memory Stability Testing (D10.20)."""

import pytest
from core.optimization.soak import SoakTester


def test_short_soak_run(tmp_path):
    tester = SoakTester(output_dir=str(tmp_path))
    # Run a short 2-second soak test at 30 FPS
    report = tester.run_soak(duration_seconds=2, target_fps=30)

    assert "verdict" in report
    assert report["verdict"] in ("PASS", "WARNING")
    assert report["duration_seconds"] >= 1.8
    assert report["total_frames_evaluated"] > 0
    assert "memory" in report
    assert "startup_rss_mb" in report["memory"]
    assert "shutdown_rss_mb" in report["memory"]
    assert report["memory"]["memory_leak_detected"] is False

    # Check that report file was created
    report_file = tmp_path / "soak_report.json"
    assert report_file.exists()

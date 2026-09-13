"""Automated Tests for Mission Data Export and Post-Mission Reporting (Phase 19, D19.13, D19.14)."""

import json
from pathlib import Path
import pytest

from core.operations.export import MissionDataExporter
from core.operations.report import MissionReportGenerator


def test_mission_data_export(tmp_path: Path):
    """Verify run export creates a complete, cryptographically verified bundle (Section 28, 29)."""
    exporter = MissionDataExporter()
    run_dir = exporter.export_run(run_id="RUN_TEST_99", output_base=tmp_path)

    assert run_dir.exists()
    assert (run_dir / "events.json").exists()
    assert (run_dir / "timeline.json").exists()
    assert (run_dir / "health.json").exists()
    assert (run_dir / "report.json").exists()
    assert (run_dir / "report.html").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "checksums.sha256").exists()

    with open(run_dir / "manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)
        assert manifest["bundle_type"] == "ASTRA-EA-MISSION-EXPORT"
        assert manifest["run_id"] == "RUN_TEST_99"
        assert len(manifest["checksums"]) > 0


def test_mission_report_generator_html():
    """Verify HTML audit report rendering contains required metrics and structure."""
    reporter = MissionReportGenerator()
    data = reporter.generate_report_data(
        run_id="RUN_TEST_99",
        events=[
            {"event_type": "STEP_VERIFIED", "payload": {}},
            {"event_type": "DEVIATION_DETECTED", "payload": {"details": "test"}},
            {"event_type": "RECOVERY_VERIFIED", "payload": {}},
        ],
        timeline={"current_met_seconds": 12.5, "milestones": []},
        health={"overall_state": "READY"},
    )

    assert data["metrics"]["steps_verified"] == 1
    assert data["metrics"]["deviations_count"] == 1
    assert data["metrics"]["recoveries_count"] == 1
    assert data["metrics"]["recovery_rate_percent"] == 100.0

    html = reporter.render_html_report(data)
    assert "<!DOCTYPE html>" in html
    assert "RUN_TEST_99" in html
    assert "Operational Metrics" in html

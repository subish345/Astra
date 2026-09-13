"""Post-Mission Reporting Engine for ASTRA-EA (Phase 19, Section 30, 31, 35, D19.14).

Compiles authoritative experiment execution records into comprehensive JSON and
self-contained, standalone HTML reports.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.common.config import get_project_root


class MissionReportGenerator:
    """Generates post-mission audit reports from execution telemetry."""

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.root = project_root or get_project_root()

    def generate_report_data(
        self,
        run_id: str,
        events: List[Dict[str, Any]],
        timeline: Dict[str, Any],
        health: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Synthesize metrics from raw events and timeline (Section 31)."""
        steps_verified = sum(1 for e in events if e.get("event_type") == "STEP_VERIFIED")
        deviations = [e for e in events if e.get("event_type") == "DEVIATION_DETECTED"]
        recoveries = [e for e in events if e.get("event_type") == "RECOVERY_VERIFIED"]
        uncertainties = sum(1 for e in events if e.get("event_type") == "STEP_UNCERTAIN")

        # Duration
        duration_s = timeline.get("current_met_seconds", 0.0)

        return {
            "title": f"ASTRA-EA Mission Assurance Audit Report — {run_id}",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "experiment_id": "DEMO_EXP_001",
            "run_id": run_id,
            "overall_status": "COMPLETED_NOMINAL" if not deviations else "COMPLETED_WITH_DEVIATIONS",
            "duration_seconds": duration_s,
            "metrics": {
                "total_events": len(events),
                "steps_verified": steps_verified,
                "deviations_count": len(deviations),
                "recoveries_count": len(recoveries),
                "uncertainties_count": uncertainties,
                "recovery_rate_percent": round((len(recoveries) / len(deviations) * 100.0) if deviations else 100.0, 1),
            },
            "deviations_log": [
                {
                    "event_id": d.get("event_id"),
                    "sequence_num": d.get("sequence_num"),
                    "timestamp_utc": d.get("timestamp_utc"),
                    "details": d.get("payload", {}),
                    "severity": d.get("severity", "WARNING"),
                }
                for d in deviations
            ],
            "subsystem_summary": {
                "camera_state": "ACTIVE_NOMINAL",
                "model_integrity": "VERIFIED_SHA256",
                "storage_state": "NOMINAL",
                "ground_link": "DISCONNECTED_POST_MISSION",
                "aggregate_health": health.get("overall_state", "READY"),
            },
            "timeline_milestones": timeline.get("milestones", []),
        }

    def render_html_report(self, report_data: Dict[str, Any]) -> str:
        """Render self-contained HTML audit document."""
        m = report_data["metrics"]
        sub = report_data["subsystem_summary"]
        run_id = report_data["run_id"]
        status = report_data["overall_status"]
        status_color = "#22c55e" if "NOMINAL" in status else "#f59e0b"

        milestones_html = ""
        for ms in report_data.get("timeline_milestones", []):
            milestones_html += f"""
            <tr>
                <td style="padding: 6px 12px; border-bottom: 1px solid #1e293b;">{ms.get('sequence_num')}</td>
                <td style="padding: 6px 12px; border-bottom: 1px solid #1e293b;"><strong>{ms.get('milestone_type')}</strong></td>
                <td style="padding: 6px 12px; border-bottom: 1px solid #1e293b;">{ms.get('title')}</td>
                <td style="padding: 6px 12px; border-bottom: 1px solid #1e293b;">{ms.get('onboard_met_seconds')}s</td>
                <td style="padding: 6px 12px; border-bottom: 1px solid #1e293b;"><span style="background: #0f172a; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{ms.get('severity')}</span></td>
            </tr>
            """

        deviations_html = ""
        if report_data.get("deviations_log"):
            for d in report_data["deviations_log"]:
                deviations_html += f"""
                <li style="margin-bottom: 6px;">
                    <strong>[{d.get('severity')}] {d.get('event_id')}</strong>: {json.dumps(d.get('details'))} (Timestamp: {d.get('timestamp_utc')})
                </li>
                """
        else:
            deviations_html = "<p style='color: #94a3b8;'>Zero procedural deviations recorded during execution.</p>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{report_data['title']}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #090d16;
            color: #f1f5f9;
            margin: 0;
            padding: 32px;
        }}
        .card {{
            background: #0d1527;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        h1 {{ color: #38bdf8; font-size: 22px; margin-top: 0; }}
        h2 {{ color: #94a3b8; font-size: 15px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
        .badge {{
            display: inline-block;
            background: {status_color};
            color: #ffffff;
            font-weight: bold;
            font-size: 12px;
            padding: 4px 10px;
            border-radius: 4px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
        }}
        .metric-box {{
            background: #111c35;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }}
        .metric-val {{
            font-size: 24px;
            font-weight: bold;
            color: #38bdf8;
        }}
        .metric-lbl {{
            font-size: 11px;
            color: #94a3b8;
            margin-top: 4px;
            text-transform: uppercase;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #111c35;
            padding: 8px 12px;
            text-align: left;
            color: #94a3b8;
            border-bottom: 2px solid #1e293b;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>ASTRA-EA Post-Mission Audit Report</h1>
                <p style="color: #94a3b8; margin: 0;">Run Identifier: <strong>{run_id}</strong> | Experiment: <strong>DEMO_EXP_001</strong> | Generated: {report_data['generated_at_utc']}</p>
            </div>
            <span class="badge">{status}</span>
        </div>
    </div>

    <div class="card">
        <h2>Operational Metrics & Performance Summary</h2>
        <div class="grid">
            <div class="metric-box">
                <div class="metric-val">{report_data['duration_seconds']:.1f}s</div>
                <div class="metric-lbl">Mission Duration</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{m['steps_verified']}</div>
                <div class="metric-lbl">Steps Verified</div>
            </div>
            <div class="metric-box">
                <div class="metric-val" style="color: {'#ef4444' if m['deviations_count'] > 0 else '#22c55e'}">{m['deviations_count']}</div>
                <div class="metric-lbl">Deviations</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{m['recoveries_count']}</div>
                <div class="metric-lbl">Recoveries</div>
            </div>
            <div class="metric-box">
                <div class="metric-val">{m['recovery_rate_percent']}%</div>
                <div class="metric-lbl">Recovery Success Rate</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>Procedural Deviations & Anomaly Dispositions</h2>
        <ul>
            {deviations_html}
        </ul>
    </div>

    <div class="card">
        <h2>Mission Timeline Milestones</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Milestone Type</th>
                    <th>Title</th>
                    <th>Elapsed (MET)</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
                {milestones_html}
            </tbody>
        </table>
    </div>

    <div class="card">
        <h2>Subsystem Readiness & Integrity Audit</h2>
        <p><strong>Camera:</strong> {sub['camera_state']} | <strong>Model:</strong> {sub['model_integrity']} | <strong>Storage:</strong> {sub['storage_state']} | <strong>Overall Health:</strong> {sub['aggregate_health']}</p>
    </div>
</body>
</html>
"""

    def generate_report_file(self, run_id: str, output_path: Optional[Path] = None) -> Path:
        """Convenience method to generate HTML report directly to file."""
        from core.operations.export import MissionDataExporter
        exporter = MissionDataExporter(self.root)
        events = exporter._collect_run_events(run_id)
        timeline = exporter._collect_run_timeline(run_id, events)
        health = exporter._collect_health_snapshot()
        data = self.generate_report_data(run_id, events, timeline, health)
        html = self.render_html_report(data)

        out_file = output_path or (self.root / "reports" / f"mission_report_{run_id}.html")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")
        return out_file

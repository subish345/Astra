"""Simulation and Resilience Report Generator for ASTRA-EA.

Outputs comprehensive JSON and visual HTML scorecards evaluating system
robustness, MTTD, MTTR, false alarm rates, and pipeline stability under fault stress.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from core.simulation.engine import SimulationRunResult


class SimulationReporter:
    """Generates visual and structured simulation reports."""

    def __init__(self, output_dir: str = "storage/reports/simulation") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_single_report(
        self,
        result: SimulationRunResult,
        filename_prefix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Save report for an individual scenario run."""
        prefix = filename_prefix or result.scenario_id.lower()
        json_path = self.output_dir / f"{prefix}_report.json"
        html_path = self.output_dir / f"{prefix}_report.html"

        data = result.model_dump()
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self._write_html_single(result, html_path)
        data["json_report"] = str(json_path)
        data["html_report"] = str(html_path)
        return data

    def generate_scenario_report(
        self,
        result: SimulationRunResult,
        filename_prefix: Optional[str] = None,
    ) -> Dict[str, str]:
        """Save scenario report and return report file paths."""
        res = self.generate_single_report(result, filename_prefix=filename_prefix)
        return {
            "json_report": res["json_report"],
            "html_report": res["html_report"],
        }


    def generate_matrix_report(
        self,
        results: List[SimulationRunResult],
        matrix_name: str = "Full Simulation Fault Matrix",
    ) -> Dict[str, Any]:
        """Save aggregated report across a matrix batch."""
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r.evaluation_verdict == "PASS")
        avg_resilience = float(np.mean([r.resilience_score for r in results])) if results else 100.0
        total_frames = sum(r.frames_processed for r in results)
        total_crashes = sum(r.pipeline_crashes for r in results)
        total_fp = sum(r.false_positive_deviations for r in results)

        summary = {
            "matrix_name": matrix_name,
            "total_scenarios": total_scenarios,
            "passed_scenarios": passed_scenarios,
            "pass_rate": round((passed_scenarios / max(1, total_scenarios)) * 100.0, 1),
            "average_resilience_score": round(avg_resilience, 1),
            "total_frames_evaluated": total_frames,
            "total_crashes": total_crashes,
            "total_false_positive_deviations": total_fp,
            "scenario_results": [r.model_dump() for r in results],
        }

        # Save files
        json_path = self.output_dir / "simulation_matrix_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        html_path = self.output_dir / "simulation_matrix_report.html"
        self._write_html_matrix(summary, results, html_path)

        return summary

    def _write_html_single(self, res: SimulationRunResult, path: Path) -> None:
        """Write visual HTML report for a single run."""
        badge_color = "#10b981" if res.evaluation_verdict == "PASS" else "#ef4444"
        history_rows = ""
        for d in res.decision_history:
            d_color = "#10b981" if d.decision_type == "VERIFIED" else ("#f59e0b" if d.decision_type == "UNCERTAIN" else "#ef4444")
            f_str = ", ".join(d.active_faults) if d.active_faults else "None (Nominal)"
            history_rows += f"""<tr>
                <td>{d.sim_time:.2f}s</td>
                <td>#{d.frame_id}</td>
                <td>{d.step_id or 'N/A'}</td>
                <td><span style="color:{d_color}; font-weight:bold;">{d.decision_type}</span></td>
                <td>{d.confidence:.2f}</td>
                <td>{f_str}</td>
                <td>{d.reason}</td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Simulation Run — {res.scenario_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: bold; background: {badge_color}; color: white; }}
        .metric-badge {{ display: inline-block; padding: 8px 16px; border-radius: 6px; background: #0f172a; border: 1px solid #334155; margin-right: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Simulation Scenario Report</h1>
        <p><strong>Scenario:</strong> {res.scenario_name} (<code>{res.scenario_id}</code>) | <span class="badge">{res.evaluation_verdict}</span></p>
        <div style="margin-top: 16px;">
            <div class="metric-badge">Resilience: <strong>{res.resilience_score:.1f}%</strong></div>
            <div class="metric-badge">Frames Processed: <strong>{res.frames_processed}</strong></div>
            <div class="metric-badge">Decisions: <strong>{res.decisions_count}</strong></div>
            <div class="metric-badge">Verified / Uncertain / Deviation: <strong>{res.verified_count} / {res.uncertain_count} / {res.deviation_count}</strong></div>
            <div class="metric-badge">MTTD: <strong>{f'{res.mean_to_detect_sec:.2f}s' if res.mean_to_detect_sec is not None else 'N/A'}</strong></div>
            <div class="metric-badge">Pipeline Crashes: <strong>{res.pipeline_crashes}</strong></div>
        </div>
    </div>

    <div class="card">
        <h2>Decision & Fault Injection History</h2>
        <table>
            <tr><th>Sim Time</th><th>Frame</th><th>Step</th><th>Assurance Decision</th><th>Conf</th><th>Active Faults</th><th>Reason</th></tr>
            {history_rows if history_rows else "<tr><td colspan='7'>No decisions recorded</td></tr>"}
        </table>
    </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _write_html_matrix(
        self,
        summary: Dict[str, Any],
        results: List[SimulationRunResult],
        path: Path,
    ) -> None:
        """Write visual HTML matrix report across scenarios."""
        rows = ""
        for r in results:
            v_color = "#10b981" if r.evaluation_verdict == "PASS" else "#ef4444"
            rows += f"""<tr>
                <td><strong>{r.scenario_name}</strong><br><small>{r.scenario_id}</small></td>
                <td><span style="color:{v_color}; font-weight:bold;">{r.evaluation_verdict}</span></td>
                <td><strong>{r.resilience_score:.1f}%</strong></td>
                <td>{r.frames_processed} ({r.frames_dropped} drop)</td>
                <td>{r.verified_count} / {r.uncertain_count} / {r.deviation_count}</td>
                <td>{f"{r.mean_to_detect_sec:.2f}s" if r.mean_to_detect_sec is not None else "N/A"}</td>
                <td>{r.pipeline_crashes}</td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Simulation Matrix Resilience Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        .metric-badge {{ display: inline-block; padding: 8px 16px; border-radius: 6px; background: #0f172a; border: 1px solid #334155; margin-right: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Simulation Matrix Resilience Report</h1>
        <p><strong>Suite:</strong> {summary['matrix_name']}</p>
        <div style="margin-top: 16px;">
            <div class="metric-badge">Average Resilience: <strong>{summary['average_resilience_score']:.1f}%</strong></div>
            <div class="metric-badge">Pass Rate: <strong>{summary['passed_scenarios']} / {summary['total_scenarios']} ({summary['pass_rate']}%)</strong></div>
            <div class="metric-badge">Total Frames: <strong>{summary['total_frames_evaluated']}</strong></div>
            <div class="metric-badge">Total Crashes: <strong>{summary['total_crashes']}</strong></div>
            <div class="metric-badge">False Alarm Deviations: <strong>{summary['total_false_positive_deviations']}</strong></div>
        </div>
    </div>

    <div class="card">
        <h2>Scenario Resilience Breakdown</h2>
        <table>
            <tr><th>Scenario</th><th>Verdict</th><th>Resilience</th><th>Frames</th><th>Ver / Unc / Dev</th><th>MTTD</th><th>Crashes</th></tr>
            {rows}
        </table>
    </div>
</body>
</html>
"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

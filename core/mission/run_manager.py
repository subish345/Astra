"""Mission Run Manager and Artifact Persistence for ASTRA-EA.

Orchestrates reproducible experiment run creation, configuration snapshots,
model snapshots, audit metadata, mission reporting (JSON + HTML), and crash recovery.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from core.common.logging import get_logger
from core.common.version import get_version_metadata

logger = get_logger("RUN_MANAGER")


class MissionRunManager:
    """Manages filesystem lifecycles and reproducible artifacts for experiment runs."""

    def __init__(self, base_dir: str = "data/runs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._current_run_dir: Optional[Path] = None
        self._current_run_id: Optional[str] = None
        self._start_time: Optional[float] = None
        self._start_utc: Optional[str] = None

    @property
    def current_run_id(self) -> Optional[str]:
        return self._current_run_id

    @property
    def current_run_dir(self) -> Optional[Path]:
        return self._current_run_dir

    def create_run(
        self,
        experiment_id: str,
        procedure_version: str = "1.0.0",
        model_profile: Optional[Dict[str, Any]] = None,
        config_snapshot: Optional[Dict[str, Any]] = None,
        camera_profile: str = "view_left",
        run_id: Optional[str] = None,
    ) -> Path:
        """Initialize a new reproducible experiment run directory."""
        now_dt = datetime.now(timezone.utc)
        self._start_utc = now_dt.isoformat()
        self._start_time = time.time()

        if run_id:
            self._current_run_id = run_id
        else:
            time_tag = now_dt.strftime("%Y%m%d_%H%M%S")
            self._current_run_id = f"RUN_{time_tag}"

        run_dir = self.base_dir / self._current_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        self._current_run_dir = run_dir

        # 1. Version metadata snapshot
        version_meta = get_version_metadata()
        with open(run_dir / "version_metadata.json", "w") as f:
            json.dump(version_meta, f, indent=2)

        # 2. Configuration snapshot
        cfg_data = config_snapshot or {}
        with open(run_dir / "config_snapshot.yaml", "w") as f:
            yaml.safe_dump(cfg_data, f, default_flow_style=False)

        # 3. Model profile snapshot
        m_profile = model_profile or {
            "model_id": "ColorSpatialObjectDetector (Baseline)",
            "detector_type": "baseline",
            "runtime": "opencv",
            "input_resolution": [640, 640],
            "confidence_threshold": 0.5,
            "dataset_version": "NOT_APPLICABLE",
        }
        with open(run_dir / "model_snapshot.json", "w") as f:
            json.dump(m_profile, f, indent=2)

        # 4. Initial run status manifest
        run_manifest = {
            "run_id": self._current_run_id,
            "experiment_id": experiment_id,
            "procedure_version": procedure_version,
            "camera_profile": camera_profile,
            "start_time_utc": self._start_utc,
            "end_time_utc": None,
            "status": "IN_PROGRESS",
            "duration_seconds": 0.0,
            "software_version": version_meta["version"],
            "git_commit": version_meta["git_commit"],
        }
        with open(run_dir / "run_metadata.json", "w") as f:
            json.dump(run_manifest, f, indent=2)

        logger.info("Created mission run: %s in %s", self._current_run_id, run_dir)
        return run_dir

    def finalize_run(
        self,
        status: str = "COMPLETED",
        total_steps: int = 0,
        completed_steps: int = 0,
        deviations_count: int = 0,
        recoveries_count: int = 0,
        uncertain_count: int = 0,
        events: Optional[List[Dict[str, Any]]] = None,
        timeline: Optional[List[Dict[str, Any]]] = None,
        health_summary: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Finalize run directory with comprehensive audit reports."""
        if not self._current_run_dir or not self._current_run_dir.exists():
            raise RuntimeError("No active run directory to finalize.")

        now_dt = datetime.now(timezone.utc)
        end_utc = now_dt.isoformat()
        elapsed = (time.time() - self._start_time) if self._start_time else 0.0

        # Read initial metadata
        meta_path = self._current_run_dir / "run_metadata.json"
        manifest = {}
        if meta_path.exists():
            with open(meta_path, "r") as f:
                manifest = json.load(f)

        manifest.update({
            "status": status,
            "end_time_utc": end_utc,
            "duration_seconds": round(elapsed, 2),
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "deviations_count": deviations_count,
            "recoveries_count": recoveries_count,
            "uncertain_count": uncertain_count,
            "effective_fps": metrics.get("effective_fps", 0.0) if metrics else 0.0,
        })

        with open(meta_path, "w") as f:
            json.dump(manifest, f, indent=2)

        # Write events and timeline
        with open(self._current_run_dir / "events.json", "w") as f:
            json.dump(events or [], f, indent=2)

        with open(self._current_run_dir / "timeline.json", "w") as f:
            json.dump(timeline or [], f, indent=2)

        if health_summary:
            with open(self._current_run_dir / "health_summary.json", "w") as f:
                json.dump(health_summary, f, indent=2)

        # Generate comprehensive mission_report.json
        report = {
            "report_id": f"REP_{self._current_run_id}",
            "generated_at": end_utc,
            "manifest": manifest,
            "metrics": metrics or {},
            "health": health_summary or {},
            "step_summary": {
                "total": total_steps,
                "completed": completed_steps,
                "deviations": deviations_count,
                "recoveries": recoveries_count,
                "uncertain": uncertain_count,
                "completion_rate": round(completed_steps / max(1, total_steps), 3),
            },
        }

        with open(self._current_run_dir / "mission_report.json", "w") as f:
            json.dump(report, f, indent=2)

        # Generate HTML report
        self._generate_html_report(report, self._current_run_dir / "mission_report.html")

        logger.info("Finalized run %s [%s]. Reports persisted.", self._current_run_id, status)
        return report

    def _generate_html_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Render a clean self-contained HTML mission report."""
        manifest = report.get("manifest", {})
        steps = report.get("step_summary", {})
        status = manifest.get("status", "UNKNOWN")
        status_color = "#22c55e" if status == "COMPLETED" else "#ef4444" if status in ("FAILED", "ABORTED") else "#f59e0b"

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ASTRA-EA Mission Report — {manifest.get('run_id')}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0b0f19; color: #e2e8f0; margin: 0; padding: 24px; }}
    .container {{ max-width: 900px; margin: 0 auto; background: #131b2e; border: 1px solid #1e293b; border-radius: 8px; padding: 24px; }}
    h1 {{ font-size: 24px; margin-top: 0; color: #38bdf8; border-bottom: 1px solid #1e293b; padding-bottom: 12px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-weight: bold; background: {status_color}; color: #000; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }}
    .card {{ background: #0f172a; padding: 16px; border-radius: 6px; border: 1px solid #1e293b; text-align: center; }}
    .card .val {{ font-size: 28px; font-weight: bold; color: #f8fafc; margin-top: 6px; }}
    .card .lbl {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 14px; }}
    th {{ color: #94a3b8; font-weight: 600; }}
    .footer {{ margin-top: 30px; font-size: 12px; color: #64748b; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>ASTRA-EA Mission Report — {manifest.get('run_id')}</h1>
    <p>Status: <span class="badge">{status}</span> &nbsp;|&nbsp; Experiment: <strong>{manifest.get('experiment_id')}</strong> &nbsp;|&nbsp; Duration: <strong>{manifest.get('duration_seconds')}s</strong></p>
    
    <div class="grid">
      <div class="card">
        <div class="lbl">Completed Steps</div>
        <div class="val">{steps.get('completed', 0)} / {steps.get('total', 0)}</div>
      </div>
      <div class="card">
        <div class="lbl">Deviations</div>
        <div class="val" style="color: #ef4444;">{steps.get('deviations', 0)}</div>
      </div>
      <div class="card">
        <div class="lbl">Recoveries</div>
        <div class="val" style="color: #22c55e;">{steps.get('recoveries', 0)}</div>
      </div>
    </div>

    <table>
      <tr><th>Parameter</th><th>Value</th></tr>
      <tr><td>Software Version</td><td>{manifest.get('software_version')} ({manifest.get('git_commit', 'unknown')[:7]})</td></tr>
      <tr><td>Camera Profile</td><td>{manifest.get('camera_profile')}</td></tr>
      <tr><td>Start Time (UTC)</td><td>{manifest.get('start_time_utc')}</td></tr>
      <tr><td>End Time (UTC)</td><td>{manifest.get('end_time_utc')}</td></tr>
      <tr><td>Effective FPS</td><td>{manifest.get('effective_fps', 0.0)}</td></tr>
    </table>

    <div class="footer">Autonomous Spacecraft Experiment Assurance &amp; Assistance (SIH26174) &bull; 100% Offline Air-Gapped Verification</div>
  </div>
</body>
</html>
"""
        with open(output_path, "w") as f:
            f.write(html)

    def detect_incomplete_runs(self) -> List[Dict[str, Any]]:
        """Scan base directory for runs that terminated abnormally (Crash Recovery)."""
        incomplete = []
        if not self.base_dir.exists():
            return incomplete

        for run_path in sorted(self.base_dir.glob("RUN_*")):
            if run_path.is_dir():
                meta_file = run_path / "run_metadata.json"
                report_file = run_path / "mission_report.json"
                if meta_file.exists():
                    try:
                        with open(meta_file, "r") as f:
                            meta = json.load(f)
                        st = meta.get("status", "")
                        if st in ("IN_PROGRESS", "RUNNING", "STARTING") or not report_file.exists():
                            incomplete.append({
                                "run_id": meta.get("run_id", run_path.name),
                                "status": "INCOMPLETE",
                                "path": str(run_path),
                                "start_time_utc": meta.get("start_time_utc"),
                                "experiment_id": meta.get("experiment_id"),
                            })
                    except Exception:
                        pass
        return incomplete

    def finalize_interrupted_run(self, run_id: str, reason: str = "Process interrupted unexpectedly") -> bool:
        """Mark an incomplete run as ABORTED without losing data."""
        run_path = self.base_dir / run_id
        meta_file = run_path / "run_metadata.json"
        if not meta_file.exists():
            return False

        try:
            with open(meta_file, "r") as f:
                meta = json.load(f)
            meta["status"] = "ABORTED"
            meta["end_time_utc"] = datetime.now(timezone.utc).isoformat()
            meta["interruption_reason"] = reason
            with open(meta_file, "w") as f:
                json.dump(meta, f, indent=2)
            logger.info("Marked interrupted run %s as ABORTED.", run_id)
            return True
        except Exception as e:
            logger.error("Failed to mark interrupted run %s: %s", run_id, e)
            return False

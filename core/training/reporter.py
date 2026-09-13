"""Training Run Report Generator for ASTRA-EA.

Generates HTML and JSON training reports with training/validation loss curves,
per-class performance metrics, hyperparameter configs, and device info.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.training.metadata import TrainingRunMetadata


class TrainingReporter:
    """Generates visual and structured training run reports."""

    def __init__(self, run_dir: str) -> None:
        self.run_dir = Path(run_dir)

    def generate_report(self, metadata: TrainingRunMetadata) -> Dict[str, Any]:
        """Save report files in run_dir."""
        self.run_dir.mkdir(parents=True, exist_ok=True)

        report_data = metadata.model_dump()

        # Save JSON
        json_path = self.run_dir / "training_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Save HTML
        html_path = self.run_dir / "training_report.html"
        self._write_html(metadata, html_path)

        return report_data

    def _write_html(self, meta: TrainingRunMetadata, output_path: Path) -> None:
        """Write formatted HTML training report."""
        history_rows = ""
        for h in meta.epoch_history:
            history_rows += f"""<tr>
                <td>{h.epoch}</td>
                <td>{h.train_loss:.4f}</td>
                <td>{h.val_loss:.4f}</td>
                <td>{h.val_precision:.3f}</td>
                <td>{h.val_recall:.3f}</td>
                <td><strong>{h.val_mAP50:.3f}</strong></td>
                <td>{h.epoch_duration_sec:.1f}s</td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Training Run Report — {meta.run_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: bold; background: #3b82f6; color: white; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Training Run Report</h1>
        <p><strong>Run ID:</strong> {meta.run_id} | <span class="badge">{meta.status}</span></p>
        <p><strong>Model:</strong> {meta.model_name} ({meta.model_architecture})</p>
        <p><strong>Dataset Version:</strong> {meta.dataset_version}</p>
        <p><strong>Hardware Device:</strong> {meta.device_used} ({meta.gpu_name or 'N/A'})</p>
        <p><strong>Best Epoch:</strong> {meta.best_epoch} (Best {meta.primary_metric}: <strong>{meta.best_metric_value:.3f}</strong>)</p>
        <p><strong>Duration:</strong> {meta.training_duration_sec:.1f}s</p>
    </div>

    <div class="card">
        <h2>Epoch Progression & Metrics</h2>
        <table>
            <tr>
                <th>Epoch</th>
                <th>Train Loss</th>
                <th>Val Loss</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>mAP@50</th>
                <th>Time</th>
            </tr>
            {history_rows if history_rows else "<tr><td colspan='7'>No history recorded</td></tr>"}
        </table>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

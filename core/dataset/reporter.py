"""Dataset Balance and Quality Reporter.

Computes class distributions, viewpoint representations, scenario balances,
and synthetic-to-real ratios, outputting structured JSON and HTML reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.dataset.schema import DatasetManifest, FrameDetectionAnnotation


class DatasetReporter:
    """Generates comprehensive dataset balance, distribution, and quality reports."""

    def __init__(self, dataset_dir: str) -> None:
        self.dataset_dir = Path(dataset_dir)

    def generate_report(
        self,
        manifest_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze dataset and write dataset_report.json and dataset_report.html."""
        out_path = Path(output_dir) if output_dir else self.dataset_dir
        out_path.mkdir(parents=True, exist_ok=True)

        annos_dir = self.dataset_dir / "annotations"
        if not annos_dir.exists():
            annos_dir = self.dataset_dir

        anno_files = list(annos_dir.glob("*.json"))
        anno_files = [
            p for p in anno_files
            if not p.name.startswith("dataset_") and p.name not in {"index.json", "metadata.json"}
        ]

        class_distribution: Dict[str, int] = {}
        viewpoint_distribution: Dict[str, int] = {}
        scenario_distribution: Dict[str, int] = {}
        source_distribution: Dict[str, int] = {}
        session_samples: Dict[str, int] = {}

        for f in anno_files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
            except Exception:
                continue

            sess_id = data.get("session_id", "DEFAULT")
            session_samples[sess_id] = session_samples.get(sess_id, 0) + 1

            view = data.get("camera_profile", "UNKNOWN")
            viewpoint_distribution[view] = viewpoint_distribution.get(view, 0) + 1

            scen = data.get("scenario", "UNKNOWN")
            scenario_distribution[scen] = scenario_distribution.get(scen, 0) + 1

            src = data.get("source", "UNKNOWN")
            source_distribution[src] = source_distribution.get(src, 0) + 1

            for obj in data.get("objects", []):
                cname = obj.get("class_name", "UNKNOWN")
                class_distribution[cname] = class_distribution.get(cname, 0) + 1

        total_samples = len(anno_files)
        total_objects = sum(class_distribution.values())

        # Check for imbalances
        imbalances: List[str] = []
        if total_objects > 0:
            for cname, count in class_distribution.items():
                ratio = count / total_objects
                if ratio < 0.08:
                    imbalances.append(f"Low representation for class '{cname}': {count} objects ({ratio:.1%})")

        if len(viewpoint_distribution) < 2:
            imbalances.append("Single viewpoint only. Cross-viewpoint evaluation requires at least VIEW_LEFT and VIEW_RIGHT.")

        # Check split statistics if manifest exists
        split_stats: Dict[str, Any] = {"train": 0, "validation": 0, "test": 0}
        manifest_file = Path(manifest_path) if manifest_path else self.dataset_dir / "dataset_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as fp:
                    manifest = DatasetManifest.model_validate_json(fp.read())
                split_stats["train"] = len(manifest.splits.train)
                split_stats["validation"] = len(manifest.splits.validation)
                split_stats["test"] = len(manifest.splits.test)
            except Exception:
                pass

        report: Dict[str, Any] = {
            "dataset_directory": str(self.dataset_dir),
            "total_samples": total_samples,
            "total_sessions": len(session_samples),
            "total_annotated_objects": total_objects,
            "class_distribution": class_distribution,
            "viewpoint_distribution": viewpoint_distribution,
            "scenario_distribution": scenario_distribution,
            "source_distribution": source_distribution,
            "splits": split_stats,
            "imbalances": imbalances,
        }

        # Write reports
        report_json = out_path / "dataset_report.json"
        with open(report_json, "w", encoding="utf-8") as fp:
            json.dump(report, fp, indent=2)

        report_html = out_path / "dataset_report.html"
        self._generate_html(report, report_html)

        return report

    def _generate_html(self, report: Dict[str, Any], output_path: Path) -> None:
        """Write visual HTML dataset balance report."""
        cls_rows = "".join(
            f"<tr><td>{cls}</td><td>{cnt}</td></tr>" for cls, cnt in report["class_distribution"].items()
        )
        view_rows = "".join(
            f"<tr><td>{view}</td><td>{cnt}</td></tr>" for view, cnt in report["viewpoint_distribution"].items()
        )
        scen_rows = "".join(
            f"<tr><td>{scen}</td><td>{cnt}</td></tr>" for scen, cnt in report["scenario_distribution"].items()
        )
        imb_items = "".join(
            f"<li style='color: #f59e0b;'>{item}</li>" for item in report["imbalances"]
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Dataset Balance & Quality Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
        ul {{ padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Dataset Balance & Quality Report</h1>
        <p><strong>Directory:</strong> {report['dataset_directory']}</p>
        <p><strong>Total Samples:</strong> {report['total_samples']} across {report['total_sessions']} session(s)</p>
        <p><strong>Total Annotated Objects:</strong> {report['total_annotated_objects']}</p>
        <p><strong>Splits:</strong> Train: {report['splits']['train']} | Val: {report['splits']['validation']} | Test: {report['splits']['test']}</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Class Distribution</h2>
            <table>
                <tr><th>Class</th><th>Count</th></tr>
                {cls_rows if cls_rows else "<tr><td colspan='2'>No classes found</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Viewpoint Distribution</h2>
            <table>
                <tr><th>Viewpoint Profile</th><th>Sample Count</th></tr>
                {view_rows if view_rows else "<tr><td colspan='2'>No viewpoints recorded</td></tr>"}
            </table>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Scenario Distribution</h2>
            <table>
                <tr><th>Scenario Type</th><th>Sample Count</th></tr>
                {scen_rows if scen_rows else "<tr><td colspan='2'>No scenarios recorded</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Dataset Balance Warnings</h2>
            {f"<ul>{imb_items}</ul>" if imb_items else "<p style='color: #10b981;'>Dataset is well-balanced across classes and viewpoints.</p>"}
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as fp:
            fp.write(html_content)

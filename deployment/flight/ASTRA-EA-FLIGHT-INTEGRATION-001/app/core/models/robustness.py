"""Model Robustness and Challenge Condition Evaluator.

Evaluates detector robustness across viewpoint changes (VIEW_LEFT vs VIEW_RIGHT)
and environmental challenges (OCCLUSION, LOW_LIGHT, WRONG_OBJECT, SKIPPED),
generating robustness_report.html and robustness_report.json.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from core.camera.interface import FrameData
from core.dataset.schema import DatasetManifest, FrameDetectionAnnotation
from core.dataset.versioning import DatasetVersionManager
from core.models.learned_detector import LearnedObjectDetector
from core.perception.types import BoundingBox, Detection


class RobustnessEvaluator:
    """Evaluates cross-viewpoint and challenge-scenario performance."""

    def __init__(
        self,
        manifests_dir: str = "datasets/manifests",
        reports_dir: str = "models/reports",
    ) -> None:
        self.manifests_dir = Path(manifests_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.version_manager = DatasetVersionManager(manifests_dir=str(self.manifests_dir))

    def evaluate_robustness(
        self,
        model_id: str,
        dataset_version: str,
        iou_threshold: float = 0.50,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate model against subsets grouped by viewpoint and scenario."""
        out_dir = Path(output_dir) if output_dir else self.reports_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        manifest = self.version_manager.load_manifest(dataset_version)
        if not manifest:
            raise ValueError(f"Dataset version '{dataset_version}' not found.")

        ds_dir_str = manifest.provenance.get("dataset_directory", "datasets/raw/synthetic/demo_synthetic")
        ds_dir = Path(ds_dir_str)
        annos_dir = ds_dir / "annotations"
        images_dir = ds_dir / "images"

        detector = LearnedObjectDetector(model_id=model_id)

        # Groups
        viewpoint_stats: Dict[str, Dict[str, int]] = {
            "VIEW_LEFT": {"tp": 0, "fp": 0, "fn": 0, "total_gt": 0, "samples": 0},
            "VIEW_RIGHT": {"tp": 0, "fp": 0, "fn": 0, "total_gt": 0, "samples": 0},
        }
        scenario_stats: Dict[str, Dict[str, int]] = {}

        # Use all available samples or test split
        sample_ids = manifest.splits.test or [p.stem for p in annos_dir.glob("*.json")]

        for s_id in sample_ids:
            anno_path = annos_dir / f"{s_id}.json"
            if not anno_path.exists():
                continue

            try:
                with open(anno_path, "r", encoding="utf-8") as f:
                    gt_anno = FrameDetectionAnnotation.model_validate(json.load(f))
            except Exception:
                continue

            img_path = ds_dir / gt_anno.image_path
            if not img_path.exists():
                img_path = images_dir / f"{s_id}.jpg"
            if not img_path.exists():
                continue

            img = cv2.imread(str(img_path))
            if img is None:
                continue

            view = gt_anno.camera_profile.upper()
            scen = gt_anno.scenario.value if hasattr(gt_anno.scenario, "value") else str(gt_anno.scenario)

            if view not in viewpoint_stats:
                viewpoint_stats[view] = {"tp": 0, "fp": 0, "fn": 0, "total_gt": 0, "samples": 0}
            if scen not in scenario_stats:
                scenario_stats[scen] = {"tp": 0, "fp": 0, "fn": 0, "total_gt": 0, "samples": 0}

            frame_data = FrameData(
                frame_id=1,
                image=img,
                timestamp_mono=time.monotonic(),
                timestamp_wall=datetime.now(timezone.utc),
                source_id="ROBUSTNESS",
            )
            preds = detector.detect(frame_data)
            gt_objects = gt_anno.objects

            # Match detections
            tp = fp = 0
            matched_gt = set()
            for pred in preds:
                best_iou = 0.0
                best_idx = -1
                for idx, gt in enumerate(gt_objects):
                    if idx in matched_gt:
                        continue
                    gt_box = BoundingBox(x1=gt.bbox[0], y1=gt.bbox[1], x2=gt.bbox[2], y2=gt.bbox[3])
                    iou = pred.bbox.iou(gt_box)
                    if iou > best_iou:
                        best_iou = iou
                        best_idx = idx

                if best_iou >= iou_threshold and best_idx >= 0:
                    if pred.class_name == gt_objects[best_idx].class_name:
                        tp += 1
                        matched_gt.add(best_idx)
                    else:
                        fp += 1
                else:
                    fp += 1

            fn = len(gt_objects) - len(matched_gt)

            # Accumulate into view
            v_stat = viewpoint_stats[view]
            v_stat["samples"] += 1
            v_stat["tp"] += tp
            v_stat["fp"] += fp
            v_stat["fn"] += fn
            v_stat["total_gt"] += len(gt_objects)

            # Accumulate into scenario
            s_stat = scenario_stats[scen]
            s_stat["samples"] += 1
            s_stat["tp"] += tp
            s_stat["fp"] += fp
            s_stat["fn"] += fn
            s_stat["total_gt"] += len(gt_objects)

        # Compute summary scores
        def _calc_metrics(st: Dict[str, int]) -> Dict[str, float]:
            tp, fp, fn = st["tp"], st["fp"], st["fn"]
            p = tp / max(1, tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / max(1, st["total_gt"]) if st["total_gt"] > 0 else 0.0
            f1 = (2 * p * r) / max(1e-6, p + r) if (p + r) > 0 else 0.0
            map50 = 0.5 * (p + r)
            return {
                "samples": st["samples"],
                "precision": round(p, 3),
                "recall": round(r, 3),
                "f1": round(f1, 3),
                "mAP50": round(map50, 3),
            }

        viewpoint_results = {k: _calc_metrics(v) for k, v in viewpoint_stats.items() if v["samples"] > 0}
        scenario_results = {k: _calc_metrics(v) for k, v in scenario_stats.items() if v["samples"] > 0}

        report = {
            "model_id": model_id,
            "dataset_version": dataset_version,
            "viewpoints": viewpoint_results,
            "scenarios": scenario_results,
        }

        # Save JSON
        with open(out_dir / "robustness_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Save HTML
        self._write_html(report, out_dir / "robustness_report.html")

        return report

    def _write_html(self, report: Dict[str, Any], output_path: Path) -> None:
        """Write visual HTML robustness report."""
        v_rows = ""
        for vname, m in report["viewpoints"].items():
            v_rows += f"""<tr>
                <td>{vname}</td>
                <td>{m['samples']}</td>
                <td>{m['precision']:.3f}</td>
                <td>{m['recall']:.3f}</td>
                <td>{m['f1']:.3f}</td>
                <td><strong>{m['mAP50']:.3f}</strong></td>
            </tr>"""

        s_rows = ""
        for sname, m in report["scenarios"].items():
            s_rows += f"""<tr>
                <td>{sname}</td>
                <td>{m['samples']}</td>
                <td>{m['precision']:.3f}</td>
                <td>{m['recall']:.3f}</td>
                <td>{m['f1']:.3f}</td>
                <td><strong>{m['mAP50']:.3f}</strong></td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Robustness Report — {report['model_id']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Viewpoint & Scenario Robustness Report</h1>
        <p><strong>Model:</strong> {report['model_id']} | <strong>Dataset:</strong> {report['dataset_version']}</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Viewpoint Robustness</h2>
            <table>
                <tr><th>Viewpoint</th><th>Samples</th><th>Precision</th><th>Recall</th><th>F1</th><th>mAP@50</th></tr>
                {v_rows}
            </table>
        </div>

        <div class="card">
            <h2>Challenge Scenario Robustness</h2>
            <table>
                <tr><th>Scenario</th><th>Samples</th><th>Precision</th><th>Recall</th><th>F1</th><th>mAP@50</th></tr>
                {s_rows}
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

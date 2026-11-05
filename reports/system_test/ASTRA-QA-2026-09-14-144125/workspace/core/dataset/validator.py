"""Dataset Validator & Data Leakage Detector.

Validates image integrity, annotation schemas, coordinate bounds, class labels,
and strictly enforces zero train-val-test session/sequence leakage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import cv2

from core.dataset.schema import DatasetManifest, FrameDetectionAnnotation


class DatasetValidator:
    """Validates dataset integrity and checks for cross-split leakage."""

    VALID_CLASSES = {"ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"}

    def __init__(self, dataset_dir: str) -> None:
        self.dataset_dir = Path(dataset_dir)

    def validate(
        self,
        manifest_path: Optional[str] = None,
        valid_classes: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:
        """Perform comprehensive validation and return structured report."""
        classes = valid_classes or self.VALID_CLASSES
        errors: List[str] = []
        warnings: List[str] = []

        manifest: Optional[DatasetManifest] = None
        manifest_file = Path(manifest_path) if manifest_path else self.dataset_dir / "dataset_manifest.json"
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = DatasetManifest.model_validate_json(f.read())
            except Exception as ex:
                errors.append(f"Failed to parse dataset manifest '{manifest_file}': {ex}")

        # Gather all annotation files
        annos_dir = self.dataset_dir / "annotations"
        if not annos_dir.exists():
            annos_dir = self.dataset_dir  # Flat structure fallback

        anno_files = list(annos_dir.glob("*.json"))
        # Exclude manifest / reports / index from annotation sample parsing
        anno_files = [
            p for p in anno_files
            if not p.name.startswith("dataset_") and p.name not in {"index.json", "metadata.json"}
        ]

        if not anno_files:
            errors.append(f"No annotation JSON files found in '{annos_dir}'.")

        seen_sample_ids: Set[str] = set()
        session_to_samples: Dict[str, List[str]] = {}
        sample_to_session: Dict[str, str] = {}
        valid_sample_count = 0

        for anno_file in anno_files:
            try:
                with open(anno_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                anno = FrameDetectionAnnotation.model_validate(data)
            except Exception as ex:
                errors.append(f"Corrupt or invalid schema in '{anno_file.name}': {ex}")
                continue

            sample_id = anno.sample_id
            if sample_id in seen_sample_ids:
                errors.append(f"Duplicate sample ID detected: '{sample_id}'")
            seen_sample_ids.add(sample_id)

            sess_id = anno.session_id or "DEFAULT_SESSION"
            session_to_samples.setdefault(sess_id, []).append(sample_id)
            sample_to_session[sample_id] = sess_id

            # Verify referenced image exists and can be read
            img_rel_path = anno.image_path
            img_full_path = self.dataset_dir / img_rel_path
            if not img_full_path.exists():
                # Try finding in images/ subfolder
                alt_path = self.dataset_dir / "images" / Path(img_rel_path).name
                if alt_path.exists():
                    img_full_path = alt_path
                else:
                    errors.append(f"Missing image file for sample '{sample_id}': {img_rel_path}")
                    continue

            # Check image readability with OpenCV
            img = cv2.imread(str(img_full_path))
            if img is None:
                errors.append(f"Broken or unreadable image file: '{img_full_path}'")
                continue

            h, w = img.shape[:2]
            if w != anno.width or h != anno.height:
                warnings.append(
                    f"Sample '{sample_id}' dimension mismatch: image is ({w}x{h}), annotation says ({anno.width}x{anno.height})"
                )

            # Validate object annotations
            if not anno.objects:
                warnings.append(f"Sample '{sample_id}' has zero annotated objects.")

            for obj_idx, obj in enumerate(anno.objects):
                if obj.class_name not in classes:
                    errors.append(
                        f"Sample '{sample_id}' object #{obj_idx} has unknown class: '{obj.class_name}'"
                    )

                bbox = obj.bbox
                if len(bbox) != 4:
                    errors.append(f"Sample '{sample_id}' object #{obj_idx} invalid bbox length: {bbox}")
                    continue

                x1, y1, x2, y2 = bbox
                if x1 >= x2 or y1 >= y2:
                    errors.append(f"Sample '{sample_id}' object #{obj_idx} inverted bbox coordinates: {bbox}")
                if x1 < 0 or y1 < 0 or x2 > w + 1 or y2 > h + 1:
                    errors.append(f"Sample '{sample_id}' object #{obj_idx} bbox exceeds image boundaries: {bbox} (img {w}x{h})")

            valid_sample_count += 1

        # Check for train/val/test leakage if manifest with splits is present
        leakage_issues: List[str] = []
        if manifest and manifest.splits:
            train_set = set(manifest.splits.train)
            val_set = set(manifest.splits.validation)
            test_set = set(manifest.splits.test)

            # 1. Check exact sample overlap
            train_val_overlap = train_set & val_set
            train_test_overlap = train_set & test_set
            val_test_overlap = val_set & test_set

            if train_val_overlap:
                leakage_issues.append(f"Direct sample leakage between TRAIN and VAL: {len(train_val_overlap)} sample(s)")
            if train_test_overlap:
                leakage_issues.append(f"Direct sample leakage between TRAIN and TEST: {len(train_test_overlap)} sample(s)")
            if val_test_overlap:
                leakage_issues.append(f"Direct sample leakage between VAL and TEST: {len(val_test_overlap)} sample(s)")

            # 2. Check session-level leakage (crucial rule: no session can span across splits)
            train_sessions = {sample_to_session[s] for s in train_set if s in sample_to_session}
            val_sessions = {sample_to_session[s] for s in val_set if s in sample_to_session}
            test_sessions = {sample_to_session[s] for s in test_set if s in sample_to_session}

            sess_train_val = train_sessions & val_sessions
            sess_train_test = train_sessions & test_sessions
            sess_val_test = val_sessions & test_sessions

            if sess_train_val:
                leakage_issues.append(f"Session-level leakage between TRAIN and VAL: sessions {sess_train_val}")
            if sess_train_test:
                leakage_issues.append(f"Session-level leakage between TRAIN and TEST: sessions {sess_train_test}")
            if sess_val_test:
                leakage_issues.append(f"Session-level leakage between VAL and TEST: sessions {sess_val_test}")

            errors.extend(leakage_issues)

        is_valid = len(errors) == 0
        report = {
            "dataset_dir": str(self.dataset_dir),
            "is_valid": is_valid,
            "sample_count": len(anno_files),
            "valid_sample_count": valid_sample_count,
            "session_count": len(session_to_samples),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "leakage_issues": leakage_issues,
        }

        # Save report files
        report_json_path = self.dataset_dir / "dataset_validation_report.json"
        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        report_html_path = self.dataset_dir / "dataset_validation_report.html"
        self._generate_html_report(report, report_html_path)

        return report

    def _generate_html_report(self, report: Dict[str, Any], output_path: Path) -> None:
        """Generate formatted HTML validation report."""
        status_color = "#28a745" if report["is_valid"] else "#dc3545"
        status_text = "PASSED" if report["is_valid"] else "FAILED"

        error_items = "".join(f"<li style='color: #dc3545;'>{e}</li>" for e in report["errors"])
        warning_items = "".join(f"<li style='color: #ffc107;'>{w}</li>" for w in report["warnings"])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ASTRA-EA Dataset Validation Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; background: #0f172a; color: #f8fafc; }}
        .card {{ background: #1e293b; border-radius: 8px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        h1, h2 {{ margin-top: 0; }}
        .badge {{ display: inline-block; padding: 6px 16px; border-radius: 9999px; font-weight: bold; background: {status_color}; color: white; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
        th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #94a3b8; }}
        ul {{ padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>ASTRA-EA Dataset Validation Report</h1>
        <p><strong>Target Directory:</strong> {report['dataset_dir']}</p>
        <p><strong>Status:</strong> <span class="badge">{status_text}</span></p>
    </div>

    <div class="card">
        <h2>Summary Metrics</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Samples</td><td>{report['sample_count']}</td></tr>
            <tr><td>Valid Samples</td><td>{report['valid_sample_count']}</td></tr>
            <tr><td>Unique Sessions</td><td>{report['session_count']}</td></tr>
            <tr><td>Validation Errors</td><td>{report['error_count']}</td></tr>
            <tr><td>Validation Warnings</td><td>{report['warning_count']}</td></tr>
            <tr><td>Leakage Detected</td><td>{"YES" if report['leakage_issues'] else "NO (0 cross-split leakage)"}</td></tr>
        </table>
    </div>

    <div class="card">
        <h2>Validation Errors ({report['error_count']})</h2>
        {f"<ul>{error_items}</ul>" if error_items else "<p style='color: #10b981;'>No errors detected.</p>"}
    </div>

    <div class="card">
        <h2>Validation Warnings ({report['warning_count']})</h2>
        {f"<ul>{warning_items}</ul>" if warning_items else "<p style='color: #10b981;'>No warnings detected.</p>"}
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

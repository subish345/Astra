"""Unit and integration tests for ASTRA-EA Dataset Subsystem.

Tests cover:
- Annotation and Manifest schema validation
- Synthetic dataset generator reproducibility with seeds
- Dataset validator and integrity checks
- Leakage detector enforcing zero cross-split session overlap
- Session-level dataset splitting
- Dataset version manager
- Balance and quality reporter
"""

import json
from pathlib import Path
import pytest

from core.dataset.generator import SyntheticDatasetGenerator
from core.dataset.reporter import DatasetReporter
from core.dataset.schema import (
    AnnotationSource,
    BoundingBox,
    DatasetManifest,
    DatasetSplit,
    DetectedObjectAnnotation,
    FrameDetectionAnnotation,
    ScenarioType,
)
from core.dataset.splitter import DatasetSplitter
from core.dataset.studio import DatasetStudio
from core.dataset.validator import DatasetValidator
from core.dataset.versioning import DatasetVersionManager


def test_schema_serialization():
    bbox = BoundingBox(x1=10, y1=20, x2=50, y2=80)
    assert bbox.width == 40
    assert bbox.height == 60
    assert bbox.area == 2400

    obj = DetectedObjectAnnotation(class_name="RED_BOX", bbox=[10, 20, 50, 80])
    anno = FrameDetectionAnnotation(
        sample_id="SAMPLE_001",
        image_path="images/SAMPLE_001.jpg",
        session_id="SESS_001",
        camera_profile="VIEW_LEFT",
        scenario=ScenarioType.CORRECT,
        source=AnnotationSource.SYNTHETIC,
        objects=[obj],
    )
    json_str = anno.model_dump_json()
    loaded = FrameDetectionAnnotation.model_validate_json(json_str)
    assert loaded.sample_id == "SAMPLE_001"
    assert loaded.objects[0].class_name == "RED_BOX"


def test_synthetic_generator_seed_reproducibility(tmp_path):
    gen1 = SyntheticDatasetGenerator(output_dir=str(tmp_path / "run1"))
    res1 = gen1.generate_dataset(sample_count=6, seed=42)

    gen2 = SyntheticDatasetGenerator(output_dir=str(tmp_path / "run2"))
    res2 = gen2.generate_dataset(sample_count=6, seed=42)

    assert res1["sample_count"] == res2["sample_count"]
    assert res1["class_counts"] == res2["class_counts"]

    # Verify identical bounding boxes across runs with same seed
    anno1 = json.loads((tmp_path / "run1/annotations/SYNTH_000001.json").read_text())
    anno2 = json.loads((tmp_path / "run2/annotations/SYNTH_000001.json").read_text())
    assert anno1["objects"][0]["bbox"] == anno2["objects"][0]["bbox"]


def test_session_level_dataset_splitter(tmp_path):
    gen = SyntheticDatasetGenerator(output_dir=str(tmp_path / "ds"))
    gen.generate_dataset(sample_count=16, seed=100)

    splitter = DatasetSplitter(dataset_dir=str(tmp_path / "ds"), seed=42)
    split = splitter.split_dataset()

    assert len(split.train) > 0
    assert len(split.validation) > 0
    assert len(split.test) > 0

    # Ensure no sample appears in more than one split
    train_set = set(split.train)
    val_set = set(split.validation)
    test_set = set(split.test)
    assert len(train_set & val_set) == 0
    assert len(train_set & test_set) == 0
    assert len(val_set & test_set) == 0


def test_leakage_detector_catches_session_contamination(tmp_path):
    gen = SyntheticDatasetGenerator(output_dir=str(tmp_path / "ds_leak"))
    gen.generate_dataset(sample_count=12, seed=200)

    # Artificially create a manifest with direct sample and session leakage
    manifest_path = tmp_path / "ds_leak/dataset_manifest.json"
    manifest = DatasetManifest(
        dataset_id="TEST_LEAK_DATASET",
        version="0.1.0",
        created_at="2026-09-13T00:00:00Z",
        classes=["RED_BOX", "YELLOW_BOX", "MAIN_BOX", "ASTRONAUT", "WORK_SURFACE"],
        splits=DatasetSplit(
            train=["SYNTH_000001", "SYNTH_000002"],
            validation=["SYNTH_000002", "SYNTH_000003"],  # SYNTH_000002 is direct leakage!
            test=["SYNTH_000004"],
        ),
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2))

    validator = DatasetValidator(dataset_dir=str(tmp_path / "ds_leak"))
    report = validator.validate(manifest_path=str(manifest_path))

    assert not report["is_valid"]
    assert report["error_count"] > 0
    assert len(report["leakage_issues"]) > 0
    assert any("leakage" in issue.lower() for issue in report["leakage_issues"])


def test_dataset_versioning_and_reporting(tmp_path):
    studio = DatasetStudio(workspace_root=str(tmp_path))
    synth_dir = tmp_path / "demo_synth"
    studio.synthesize(output_dir=str(synth_dir), sample_count=12, seed=300)

    # Split
    split = studio.split(dataset_path=str(synth_dir))
    assert len(split.train) + len(split.validation) + len(split.test) == 12

    # Validate
    val_report = studio.validate(dataset_path=str(synth_dir))
    assert val_report["is_valid"]
    assert val_report["error_count"] == 0

    # Version
    manifest = studio.version(
        dataset_id="ASTRA-TEST-DATASET-v1.0",
        version="1.0.0",
        dataset_path=str(synth_dir),
    )
    assert manifest.dataset_id == "ASTRA-TEST-DATASET-v1.0"
    assert manifest.sample_count == 12

    # Report
    rep = studio.report(dataset_path=str(synth_dir))
    assert rep["total_samples"] == 12
    assert rep["total_annotated_objects"] > 0
    assert (synth_dir / "dataset_report.html").exists()
    assert (synth_dir / "dataset_report.json").exists()

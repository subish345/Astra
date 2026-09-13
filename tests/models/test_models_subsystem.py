"""Unit and integration tests for ASTRA-EA Model Registry & Evaluation Subsystem.

Tests cover:
- ModelRegistry state transitions & promotion rules
- LearnedObjectDetector interface compliance (detect, model_name, get_supported_classes)
- ModelEvaluator test-set evaluation & confusion matrix
- ModelComparator baseline-vs-learned benchmarking
- Model pre-flight sanity check
- RobustnessEvaluator cross-viewpoint evaluation
"""

from datetime import datetime, timezone
from pathlib import Path
import time
import numpy as np
import pytest

from core.camera.interface import FrameData
from core.dataset.studio import DatasetStudio
from core.models.comparison import ModelComparator
from core.models.evaluator import ModelEvaluator
from core.models.learned_detector import LearnedObjectDetector
from core.models.registry import ModelRecord, ModelRegistry, ModelStatus
from core.models.robustness import RobustnessEvaluator
from core.perception.detection.interface import ObjectDetector
from core.perception.types import Detection


def test_model_registry_lifecycle(tmp_path):
    reg = ModelRegistry(registry_dir=str(tmp_path / "registry"))
    rec = ModelRecord(
        model_id="TEST_DETECTOR_v1",
        version="1.0.0",
        dataset_version="ASTRA-DATASET-v0.1",
        training_run="RUN_001",
        status=ModelStatus.CANDIDATE,
    )
    reg.register_model(rec)

    # Attempting to promote to VALIDATED without metrics must fail
    with pytest.raises(ValueError):
        reg.update_status("TEST_DETECTOR_v1", ModelStatus.VALIDATED)

    # Add metrics and promote
    rec.metrics = {"mAP50": 0.88}
    reg.register_model(rec)
    updated = reg.update_status("TEST_DETECTOR_v1", ModelStatus.VALIDATED)
    assert updated.status == ModelStatus.VALIDATED

    # Set deployment candidate
    dep = reg.set_deployment_candidate("TEST_DETECTOR_v1")
    assert dep.status == ModelStatus.DEPLOYMENT_CANDIDATE


def test_learned_object_detector_interface_compliance():
    detector = LearnedObjectDetector(
        model_id="ASTRA_OBJECT_DETECTOR_v0.1.0",
        fallback_to_baseline=True,
    )
    assert isinstance(detector, ObjectDetector)
    assert "ASTRONAUT" in detector.get_supported_classes()
    assert "RED_BOX" in detector.get_supported_classes()
    assert len(detector.model_name) > 0

    # Test inference on dummy frame
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = FrameData(
        frame_id=1,
        image=img,
        timestamp_mono=time.monotonic(),
        timestamp_wall=datetime.now(timezone.utc),
        source_id="TEST",
    )
    dets = detector.detect(frame)
    assert isinstance(dets, list)
    for d in dets:
        assert isinstance(d, Detection)


def test_model_evaluator_and_comparator(tmp_path):
    # Prepare minimal synthetic dataset in tmp_path
    studio = DatasetStudio(workspace_root=str(tmp_path))
    ds_dir = tmp_path / "test_eval_ds"
    studio.synthesize(output_dir=str(ds_dir), sample_count=10, seed=555)
    studio.split(dataset_path=str(ds_dir))
    manifest = studio.version(
        dataset_id="TEST-EVAL-DATASET",
        version="0.1.0",
        dataset_path=str(ds_dir),
    )

    evaluator = ModelEvaluator(
        manifests_dir=str(tmp_path / "datasets/manifests"),
        registry_dir=str(tmp_path / "models/registry"),
        reports_dir=str(tmp_path / "models/reports"),
    )

    # Sanity check
    sanity = evaluator.validate_model_sanity("ASTRA_OBJECT_DETECTOR_v0.1.0")
    assert "all_passed" in sanity

    # Evaluation
    eval_res = evaluator.evaluate(
        model_id="ASTRA_OBJECT_DETECTOR_v0.1.0",
        dataset_version="TEST-EVAL-DATASET",
        output_dir=str(tmp_path / "models/reports"),
    )
    assert "overall_metrics" in eval_res
    assert "mAP50" in eval_res["overall_metrics"]
    assert "confusion_matrix" in eval_res
    assert (tmp_path / "models/reports/model_evaluation_report.html").exists()

    # Comparison
    comparator = ModelComparator(
        manifests_dir=str(tmp_path / "datasets/manifests"),
        reports_dir=str(tmp_path / "models/reports"),
    )
    comp_res = comparator.compare(
        baseline_name="ColorSpatialObjectDetector",
        learned_model_id="ASTRA_OBJECT_DETECTOR_v0.1.0",
        dataset_version="TEST-EVAL-DATASET",
        output_dir=str(tmp_path / "models/reports"),
    )
    assert "baseline" in comp_res
    assert "learned_model" in comp_res
    assert "recommendation" in comp_res["comparison"]
    assert (tmp_path / "models/reports/model_comparison_report.html").exists()

    # Robustness
    rob = RobustnessEvaluator(
        manifests_dir=str(tmp_path / "datasets/manifests"),
        reports_dir=str(tmp_path / "models/reports"),
    )
    rob_res = rob.evaluate_robustness(
        model_id="ASTRA_OBJECT_DETECTOR_v0.1.0",
        dataset_version="TEST-EVAL-DATASET",
        output_dir=str(tmp_path / "models/reports"),
    )
    assert "viewpoints" in rob_res
    assert (tmp_path / "models/reports/robustness_report.html").exists()

"""Automated tests for Inference Runtime, ONNX Export, Resource Budget, and Deployment Profiles (D10.13 - D10.19, D10.23)."""

from pathlib import Path
import numpy as np
import pytest

from core.optimization.runtime import (
    InferenceRuntime,
    OpenCVDNNRuntime,
    RuntimeFactory,
)
from core.optimization.onnx_export import ModelExporter, ONNXValidator
from core.optimization.budget import ResourceBudget, BudgetMonitor
from core.optimization.profiles import DeploymentProfileManager
from core.optimization.compatibility import ModelCompatibilityMatrix
from core.optimization.quantization import ModelOptimizationEvaluator


def test_deployment_profile_manager():
    profiles = DeploymentProfileManager.list_profiles()
    assert "development" in profiles
    assert "balanced" in profiles
    assert "realtime" in profiles
    assert "low_resource" in profiles

    # Load balanced profile
    balanced = DeploymentProfileManager.load_profile("balanced")
    assert "profile_name" in balanced
    assert "BALANCED" in balanced["profile_name"]
    assert "scheduler" in balanced
    assert "resources" in balanced
    assert "perception" in balanced

    # Load realtime profile
    realtime = DeploymentProfileManager.load_profile("realtime")
    assert "REALTIME" in realtime["profile_name"]
    assert realtime["scheduler"]["detection_interval"] >= 1


def test_resource_budget_and_monitor():
    # Strict budget to trigger limits
    strict_budget = ResourceBudget(
        max_ram_gb=0.0001,  # Unreasonably small, should trigger violation
        max_gpu_memory_gb=10.0,
        max_cpu_percent=100.0,
        max_queue_size=2,
    )
    monitor = BudgetMonitor(budget=strict_budget)
    res = monitor.check_limits(current_queue_size=1)
    assert monitor.is_degraded is True
    assert len(monitor.violations) >= 1
    assert any("RAM exceeded" in v for v in monitor.violations)

    # Generous budget
    generous_budget = ResourceBudget(
        max_ram_gb=64.0,
        max_gpu_memory_gb=32.0,
        max_cpu_percent=100.0,
        max_queue_size=100,
    )
    monitor2 = BudgetMonitor(budget=generous_budget)
    res2 = monitor2.check_limits(current_queue_size=0)
    assert monitor2.is_degraded is False
    assert len(monitor2.violations) == 0

    # Queue limit breach
    res3 = monitor2.check_limits(current_queue_size=150)
    assert monitor2.is_degraded is True
    assert any("Queue backpressure" in v for v in monitor2.violations)


def test_onnx_export_validation_and_runtime(tmp_path):
    out_file = tmp_path / "test_detector.onnx"
    exported_path = ModelExporter.export_to_onnx(
        model_id="TEST_DETECTOR",
        output_path=out_file,
        input_size=(640, 640),
        classes=["ASTRONAUT", "MAIN_BOX", "RED_BOX", "YELLOW_BOX", "WORK_SURFACE"],
    )
    assert exported_path.exists()
    assert exported_path.with_suffix(".onnx.json").exists()

    # Pre-flight validation
    val_result = ONNXValidator.validate(exported_path)
    assert val_result["status"] == "PASS"
    assert val_result["checks"]["onnx_proto_valid"] is True
    assert val_result["checks"]["opencv_dnn_load"] is True
    assert val_result["checks"]["forward_pass_success"] is True
    assert val_result["checks"]["zero_nans"] is True
    assert val_result["checks"]["zero_infs"] is True
    assert val_result["input_shape"] == [1, 3, 640, 640]

    # Load into OpenCVDNNRuntime and run forward pass
    runtime = RuntimeFactory.create(runtime_type="opencv_dnn", input_size=(640, 640))
    loaded = runtime.load(exported_path)
    assert loaded is True
    assert runtime.is_loaded is True

    test_img = np.zeros((480, 640, 3), dtype=np.uint8)
    output = runtime.predict(test_img)
    assert output is not None
    assert output.ndim == 3  # [1, 9, 8400]
    assert output.shape[1] == 9
    assert output.shape[2] == 8400

    stats = runtime.get_latency_stats()
    assert stats["inference_count"] == 1
    assert stats["mean_inference_ms"] > 0.0


def test_model_optimization_evaluator():
    evaluator = ModelOptimizationEvaluator()
    summary = evaluator.run_suite()
    assert "baseline" in summary
    assert "variants" in summary
    assert len(summary["variants"]) >= 2
    assert "recommended_variant" in summary

    # Verify critical classes in baseline metrics
    baseline = summary["baseline"]
    assert "red_box_recall" in baseline
    assert "yellow_box_recall" in baseline
    assert baseline["red_box_recall"] > 0.0


def test_model_compatibility_matrix(tmp_path):
    matrix = ModelCompatibilityMatrix(output_dir=str(tmp_path))
    res = matrix.generate_matrix()
    assert "models" in res
    assert "platform" in res
    assert len(res["models"]) >= 2
    # Baseline model should support CPU
    baseline_entry = next(e for e in res["models"] if "Baseline" in e["model_id"])
    assert baseline_entry["cpu"] is True


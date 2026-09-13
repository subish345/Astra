"""Unit tests for ML Environment Doctor."""

import pytest
from core.cli.ml_doctor import inspect_ml_environment, run_ml_doctor


def test_inspect_ml_environment_returns_required_keys():
    info = inspect_ml_environment()
    assert "python_version" in info
    assert "pytorch_available" in info
    assert "cuda_available" in info
    assert "status" in info
    assert "tensor_test" in info
    assert info["status"] in {"AVAILABLE", "CPU_FALLBACK", "BLOCKED", "DEGRADED"}


def test_ml_doctor_execution(capsys):
    ret = run_ml_doctor()
    captured = capsys.readouterr()
    assert "ASTRA-EA ML ENVIRONMENT" in captured.out
    assert "Python:" in captured.out
    assert "PyTorch:" in captured.out
    assert "ML ENVIRONMENT STATUS:" in captured.out
    assert ret in (0, 1)

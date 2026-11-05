"""ASTRA-EA Optimization, Benchmarking, and Deployment Framework."""

from core.optimization.backend import (
    ComputeBackend,
    CPUBackend,
    CUDABackend,
    FutureEdgeBackend,
    PlatformInspector,
    PlatformTelemetry,
)
from core.optimization.budget import BudgetMonitor, ResourceBudget
from core.optimization.compatibility import ModelCompatibilityMatrix
from core.optimization.onnx_export import ModelExporter, ONNXValidator
from core.optimization.profiles import DeploymentProfileManager
from core.optimization.runner import BenchmarkRunner
from core.optimization.profiler import PipelineProfiler, calculate_percentiles
from core.optimization.quantization import ModelOptimizationEvaluator, OptimizationEvaluation
from core.optimization.runtime import (
    InferenceRuntime,
    ONNXRuntimeEngine,
    OpenCVDNNRuntime,
    RuntimeFactory,
)
from core.optimization.scheduler import (
    AdaptiveInferenceScheduler,
    LatestFrameQueue,
    SchedulerCadence,
)
from core.optimization.soak import SoakTester

__all__ = [
    "ComputeBackend",
    "CPUBackend",
    "CUDABackend",
    "FutureEdgeBackend",
    "PlatformInspector",
    "PlatformTelemetry",
    "ResourceBudget",
    "BudgetMonitor",
    "ModelCompatibilityMatrix",
    "ModelExporter",
    "ONNXValidator",
    "PipelineProfiler",
    "calculate_percentiles",
    "ModelOptimizationEvaluator",
    "OptimizationEvaluation",
    "InferenceRuntime",
    "OpenCVDNNRuntime",
    "ONNXRuntimeEngine",
    "RuntimeFactory",
    "AdaptiveInferenceScheduler",
    "LatestFrameQueue",
    "SchedulerCadence",
    "SoakTester",
]

"""ASTRA-EA physical activity recognition and temporal reasoning subsystem."""

from core.activity.annotation import (
    ActivityAnnotation,
    export_annotations_json,
    export_annotations_jsonl,
)
from core.activity.benchmark import ActivityBenchmark, Phase3BenchmarkReport
from core.activity.composite import CompositeActivityEngine
from core.activity.confidence import ActivityConfidenceEngine
from core.activity.events import (
    ActivityCancelledEvent,
    ActivityConfirmedEvent,
    ActivityEndedEvent,
    ActivityEventBus,
    ActivityEventDeduplicator,
    ActivityStartedEvent,
    ActivityUncertainEvent,
    ActivityUpdatedEvent,
    InteractionConfirmedEvent,
    InteractionEndedEvent,
    InteractionStartedEvent,
    InteractionUpdatedEvent,
)
from core.activity.interface import ActivityRecognizer, StubActivityRecognizer
from core.activity.primitive import PrimitiveActivityEngine
from core.activity.temporal import TemporalBuffer, TemporalFeatureExtractor
from core.activity.types import (
    ActivityConfidenceLevel,
    ActivityObservation,
    ActivityStatus,
    CompositeActivityType,
    PrimitiveActivityType,
    TemporalFeatureSet,
    TemporalWindow,
)
from core.activity.visualizer import ActivityVisualizer

__all__ = [
    "ActivityRecognizer",
    "StubActivityRecognizer",
    "PrimitiveActivityEngine",
    "CompositeActivityEngine",
    "ActivityConfidenceEngine",
    "TemporalBuffer",
    "TemporalFeatureExtractor",
    "ActivityVisualizer",
    "ActivityBenchmark",
    "Phase3BenchmarkReport",
    "ActivityAnnotation",
    "export_annotations_json",
    "export_annotations_jsonl",
    "ActivityEventBus",
    "ActivityEventDeduplicator",
    "PrimitiveActivityType",
    "CompositeActivityType",
    "ActivityStatus",
    "ActivityConfidenceLevel",
    "TemporalFeatureSet",
    "TemporalWindow",
    "ActivityObservation",
    "InteractionStartedEvent",
    "InteractionUpdatedEvent",
    "InteractionConfirmedEvent",
    "InteractionEndedEvent",
    "ActivityStartedEvent",
    "ActivityUpdatedEvent",
    "ActivityConfirmedEvent",
    "ActivityUncertainEvent",
    "ActivityCancelledEvent",
    "ActivityEndedEvent",
]

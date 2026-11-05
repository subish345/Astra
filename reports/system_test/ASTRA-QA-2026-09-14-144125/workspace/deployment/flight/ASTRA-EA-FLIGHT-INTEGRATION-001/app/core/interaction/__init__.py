"""ASTRA-EA physical interaction recognition subsystem."""

from core.interaction.engine import SpatialInteractionEngine
from core.interaction.geometry import (
    calculate_box_overlap_iou,
    calculate_normalized_distance,
    calculate_pixel_distance,
    compute_approach_speed,
    compute_motion_correlation,
    compute_velocity_vector,
    determine_relative_position,
)
from core.interaction.interface import InteractionEngine, StubInteractionEngine
from core.interaction.rules import InteractionRules
from core.interaction.state_machine import HandObjectStateMachine
from core.interaction.types import InteractionEvent, InteractionState, SpatialRelationship
from core.interaction.visualizer import InteractionVisualizer

__all__ = [
    "InteractionEngine",
    "StubInteractionEngine",
    "SpatialInteractionEngine",
    "InteractionState",
    "SpatialRelationship",
    "InteractionEvent",
    "InteractionRules",
    "HandObjectStateMachine",
    "InteractionVisualizer",
    "calculate_pixel_distance",
    "calculate_normalized_distance",
    "calculate_box_overlap_iou",
    "determine_relative_position",
    "compute_velocity_vector",
    "compute_motion_correlation",
    "compute_approach_speed",
]

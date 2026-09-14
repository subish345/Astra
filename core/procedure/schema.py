"""Pydantic schema definitions for ASTRA-EA experiment procedures.

Defines strongly-typed structures for experiment metadata, tracked objects,
steps, expected actions, multimodal evidence requirements, and recovery guidance.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ActionPrimitive(str, Enum):
    """Primitive human-object action concepts recognized by ASTRA-EA."""
    IDLE = "IDLE"
    APPROACH = "APPROACH"
    REACH = "REACH"
    TOUCH = "TOUCH"
    GRASP = "GRASP"
    LIFT = "LIFT"
    HOLD = "HOLD"
    MOVE = "MOVE"
    CARRY = "CARRY"
    PLACE = "PLACE"
    RELEASE = "RELEASE"
    PUSH = "PUSH"
    PULL = "PULL"
    PRESS = "PRESS"
    POUR = "POUR"
    MIX = "MIX"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    INSERT = "INSERT"
    REMOVE = "REMOVE"
    APPROACH_DESTINATION = "APPROACH_DESTINATION"


class StepCriticality(str, Enum):
    """Criticality level determining alert urgency upon deviation."""
    INFO = "INFO"
    GUIDANCE = "GUIDANCE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ExperimentObject(BaseModel):
    """Definition of an object involved in the scientific experiment."""
    id: str = Field(..., description="Unique alphanumeric identifier (e.g. 'RED_BOX')")
    name: str = Field(..., description="Human-readable object name")
    category: str = Field(default="general", description="Functional category (e.g. 'container', 'sample')")
    color: Optional[str] = Field(default=None, description="Color attribute for visual disambiguation")
    description: Optional[str] = Field(default=None, description="Detailed physical description")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary custom properties")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Object ID cannot be empty.")
        return v


class ZoneDefinition(BaseModel):
    """Spatial zone for procedural approach and workstation grounding."""
    id: str = Field(..., description="Unique zone identifier (e.g. 'EXPERIMENT_STATION')")
    name: Optional[str] = Field(default=None, description="Human-readable zone name")
    type: str = Field(default="rectangle", description="Zone geometry type (e.g. 'rectangle', 'polygon')")
    coordinates: List[float] = Field(default_factory=list, description="Normalized coordinates [x1, y1, x2, y2]")
    description: Optional[str] = Field(default=None, description="Operational description")

    @field_validator("id")
    @classmethod
    def validate_zone_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Zone ID cannot be empty.")
        return v


class DestinationRule(BaseModel):
    """Destination validation requirements for object transfer and placement."""
    object: Optional[str] = Field(default=None, description="Destination target object ID (e.g. 'WORK_SURFACE')")
    zone: Optional[str] = Field(default=None, description="Destination target zone ID (e.g. 'WORK_SURFACE_ZONE')")
    max_distance: float = Field(default=0.25, ge=0.0, description="Maximum normalized distance to destination")


class StabilizationRule(BaseModel):
    """Physical stabilization criteria for placed objects."""
    minimum_duration_seconds: float = Field(default=0.75, ge=0.0, description="Minimum duration object must remain stable")
    maximum_position_delta: float = Field(default=0.05, ge=0.0, description="Maximum allowable normalized position displacement")


class RecoveryInstruction(BaseModel):
    """Guidance provided to the astronaut to recover from a procedural deviation."""
    instruction: str = Field(..., description="Vocalized and displayed recovery guidance")
    target_step: Optional[str] = Field(default=None, description="Step ID to return to upon recovery")
    max_recovery_time_seconds: float = Field(default=60.0, gt=0.0)


class EvidencePathRule(BaseModel):
    """Structured rule for evaluating alternate or grouped evidence conditions."""
    all_of: Optional[List[str]] = Field(default=None, description="All listed evidence items must be satisfied")
    any_of: Optional[List[List[str]]] = Field(default=None, description="At least one listed group of evidence must be satisfied")
    one_of: Optional[List[str]] = Field(default=None, description="Exactly one of the listed evidence items must be satisfied")


class TransitionRule(BaseModel):
    """Explicit state-transition rule from one experiment step to another."""
    next: List[str] = Field(default_factory=list, description="List of valid next step IDs")
    condition: Optional[str] = Field(default=None, description="Optional condition required for this branch")


class StepCompletionRule(BaseModel):
    """Specific conditions marking the definitive completion of an experiment step."""
    type: Optional[str] = Field(default=None, description="Completion type (e.g. 'ENTER_ZONE', 'DESTINATION_MATCH', 'RELEASE')")
    zone: Optional[str] = Field(default=None, description="Target zone identifier if applicable")
    minimum_duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Minimum duration condition must hold")
    activity: Optional[str] = Field(default=None, description="Required terminating activity concept")
    object_id: Optional[str] = Field(default=None, description="Target object involved in completion")
    required_evidence: List[str] = Field(default_factory=list, description="Evidence items required for completion")


class ExperimentStep(BaseModel):
    """Individual milestone step in an experiment procedure."""
    id: str = Field(..., description="Unique step identifier (e.g. 'STEP_01')")
    sequence: int = Field(..., ge=1, description="1-indexed sequence order")
    name: str = Field(..., description="Concise human-readable step title")
    description: Optional[str] = Field(default=None, description="Detailed operational instructions")
    expected_objects: List[str] = Field(default_factory=list, description="IDs of objects interacted with")
    expected_actions: List[str] = Field(default_factory=list, description="List of ActionPrimitives")
    action_sequence: Optional[List[str]] = Field(default=None, description="Ordered sequence of sub-actions required for step")
    destination: Optional[DestinationRule] = Field(default=None, description="Destination constraints for transfer/place steps")
    stabilization: Optional[StabilizationRule] = Field(default=None, description="Stabilization constraints for placement")
    allow_unstable_placement: bool = Field(default=False, description="Allow placement verification without stillness evidence")
    required_evidence: List[str] = Field(default_factory=list, description="Mandatory evidence flags")
    optional_evidence: List[str] = Field(default_factory=list, description="Supplemental corroborating evidence")
    evidence_paths: Optional[EvidencePathRule] = Field(default=None, description="Alternate evidence groupings (any_of, all_of)")
    transitions: Optional[Any] = Field(default=None, description="Graph-based allowed transitions or next step IDs")
    completion: Optional[StepCompletionRule] = Field(default=None, description="Explicit step completion criteria")
    min_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    min_duration_seconds: float = Field(default=1.0, ge=0.0)
    repeatable: bool = Field(default=False)
    optional: bool = Field(default=False, description="Whether this step may be optionally omitted")
    criticality: StepCriticality = Field(default=StepCriticality.WARNING)
    recovery: Optional[RecoveryInstruction] = Field(default=None)

    @field_validator("id")
    @classmethod
    def validate_step_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Step ID cannot be empty.")
        return v

    @field_validator("expected_actions")
    @classmethod
    def validate_actions(cls, actions: List[str]) -> List[str]:
        cleaned = []
        for a in actions:
            act_upper = a.strip().upper()
            if act_upper not in ActionPrimitive.__members__:
                raise ValueError(f"Unknown action primitive: '{a}'. Valid actions: {list(ActionPrimitive.__members__.keys())}")
            cleaned.append(act_upper)
        return cleaned

    @field_validator("action_sequence")
    @classmethod
    def validate_action_sequence(cls, actions: Optional[List[str]]) -> Optional[List[str]]:
        if actions is None:
            return None
        cleaned = []
        for a in actions:
            act_upper = a.strip().upper()
            if act_upper not in ActionPrimitive.__members__:
                raise ValueError(f"Unknown action primitive in action_sequence: '{a}'. Valid actions: {list(ActionPrimitive.__members__.keys())}")
            cleaned.append(act_upper)
        return cleaned


class ExperimentMetadata(BaseModel):
    """High-level metadata for an experiment definition."""
    id: str = Field(..., description="Unique experiment identifier (e.g. 'DEMO_EXP_001')")
    name: str = Field(..., description="Formal experiment name")
    version: str = Field(default="1.0.0", description="Semantic procedure version")
    description: Optional[str] = Field(default=None)
    author: Optional[str] = Field(default=None)


class ExperimentDefinition(BaseModel):
    """Complete, self-contained experiment procedure configuration."""
    experiment: ExperimentMetadata
    objects: List[ExperimentObject] = Field(default_factory=list)
    zones: List[ZoneDefinition] = Field(default_factory=list, description="Spatial workstation and destination zones")
    steps: List[ExperimentStep] = Field(default_factory=list)
    continuous_observation: bool = Field(default=False, description="Keep perception running without procedural steps")
    transitions: Optional[Dict[str, Any]] = Field(default=None, description="Global experiment transition topology")

    @property
    def id(self) -> str:
        return self.experiment.id

    @property
    def name(self) -> str:
        return self.experiment.name

    @property
    def version(self) -> str:
        return self.experiment.version

    def get_step(self, step_id: str) -> Optional[ExperimentStep]:
        """Find and return a step by its unique identifier."""
        target = step_id.strip().upper()
        for s in self.steps:
            if s.id.upper() == target:
                return s
        return None

    def get_object(self, object_id: str) -> Optional[ExperimentObject]:
        """Find and return an object definition by its unique identifier."""
        target = object_id.strip().upper()
        for obj in self.objects:
            if obj.id.upper() == target:
                return obj
        return None


# Semantic alias for procedural contracts
ExperimentProcedure = ExperimentDefinition

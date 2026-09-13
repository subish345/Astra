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


class RecoveryInstruction(BaseModel):
    """Guidance provided to the astronaut to recover from a procedural deviation."""
    instruction: str = Field(..., description="Vocalized and displayed recovery guidance")
    target_step: Optional[str] = Field(default=None, description="Step ID to return to upon recovery")
    max_recovery_time_seconds: float = Field(default=60.0, gt=0.0)


class ExperimentStep(BaseModel):
    """Individual milestone step in an experiment procedure."""
    id: str = Field(..., description="Unique step identifier (e.g. 'STEP_01')")
    sequence: int = Field(..., ge=1, description="1-indexed sequence order")
    name: str = Field(..., description="Concise human-readable step title")
    description: Optional[str] = Field(default=None, description="Detailed operational instructions")
    expected_objects: List[str] = Field(default_factory=list, description="IDs of objects interacted with")
    expected_actions: List[str] = Field(default_factory=list, description="List of ActionPrimitives")
    required_evidence: List[str] = Field(default_factory=list, description="Mandatory evidence flags")
    optional_evidence: List[str] = Field(default_factory=list, description="Supplemental corroborating evidence")
    min_confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    timeout_seconds: float = Field(default=60.0, gt=0.0)
    min_duration_seconds: float = Field(default=1.0, ge=0.0)
    repeatable: bool = Field(default=False)
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
    steps: List[ExperimentStep] = Field(default_factory=list)

"""Activity recognition data structures for ASTRA-EA.

Represents temporal actions aggregated across sliding observation windows.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.interaction.types import InteractionEvent


@dataclass
class TemporalWindow:
    """Sliding time window of multi-frame observations."""
    start_time: float
    end_time: float
    interactions: List[InteractionEvent] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)


@dataclass
class ActivityObservation:
    """Classified human activity with temporal bounds and confidence score."""
    activity_name: str
    actor: str
    target_object_id: str
    confidence: float
    window: TemporalWindow
    activity_id: str = field(default_factory=lambda: f"ACT_{uuid.uuid4().hex[:8].upper()}")
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def start_time(self) -> float:
        return self.window.start_time

    @property
    def end_time(self) -> float:
        return self.window.end_time

    @property
    def duration_seconds(self) -> float:
        return self.window.duration

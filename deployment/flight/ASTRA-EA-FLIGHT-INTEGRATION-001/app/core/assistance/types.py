"""Assistance data structures for astronaut voice and visual guidance in ASTRA-EA.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from core.mission.events import AssistantPriority


@dataclass
class AssistantMessage:
    """Standardized guidance or recovery message dispatched to voice and GUI."""
    text: str
    priority: AssistantPriority = AssistantPriority.GUIDANCE
    cooldown_seconds: float = 3.5
    spoken: bool = False
    message_id: str = field(default_factory=lambda: f"MSG_{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

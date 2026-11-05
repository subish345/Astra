"""Abstract interfaces and development doubles for the ASTRA-EA assistance tier.

Handles multimodal astronaut guidance and closed-loop deviation recovery.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.assistance.types import AssistantMessage, AssistantPriority
from core.assurance.types import AssuranceDecision
from core.procedure.schema import ExperimentStep


class VoiceManager(ABC):
    """Abstract interface for local text-to-speech audio guidance."""

    @abstractmethod
    def speak(self, text: str, priority: AssistantPriority = AssistantPriority.GUIDANCE, cooldown: float = 3.5) -> bool:
        """Enqueue speech output. Returns True if successfully queued/spoken."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Immediately silence speech synthesis."""
        pass

    @property
    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if speech synthesis is currently active."""
        pass


class GuidanceEngine(ABC):
    """Abstract interface for generating contextual guidance and recovery messages."""

    @abstractmethod
    def get_step_guidance(self, step: ExperimentStep) -> AssistantMessage:
        """Generate instructional message for the current experiment step."""
        pass

    @abstractmethod
    def get_deviation_guidance(self, decision: AssuranceDecision, step: ExperimentStep) -> AssistantMessage:
        """Generate corrective recovery instructions upon procedural deviation."""
        pass


class StubVoiceManager(VoiceManager):
    """Development double recording spoken messages without audio output."""

    def __init__(self):
        self.spoken_messages: list[str] = []

    def speak(self, text: str, priority: AssistantPriority = AssistantPriority.GUIDANCE, cooldown: float = 3.5) -> bool:
        self.spoken_messages.append(text)
        return True

    def stop(self) -> None:
        pass

    @property
    def is_busy(self) -> bool:
        return False
